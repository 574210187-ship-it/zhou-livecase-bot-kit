from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from zhou_livecase.contracts import (
    AnalysisBundle,
    ContractError,
    SourceSnapshot,
    Stage,
    StageReceipt,
    WritePlan,
    validate_analysis,
    validate_receipt,
    validate_source_snapshot,
    validate_write_plan,
)


class WriteGateway(Protocol):
    """Private runtime adapter. Implementations own credentials, never Analysis AI."""

    def commit(self, plan: WritePlan, stage: Stage) -> StageReceipt: ...


class RunStore(Protocol):
    """Durable state boundary; production implementations persist atomically."""

    def load(self, run_id: str) -> "RunState | None": ...
    def save(self, state: "RunState") -> None: ...


@dataclass
class RunState:
    run_id: str
    rule_sha256: str
    input_snapshot_sha256: str
    source_snapshot: SourceSnapshot | None = None
    plans: dict[str, WritePlan] = field(default_factory=dict)
    receipts: dict[tuple[str, int, Stage], StageReceipt] = field(default_factory=dict)


class Runner:
    """Deterministic write authority with fixed stage order and stable idempotency."""

    def __init__(self, gateway: WriteGateway, store: RunStore | None = None):
        self._gateway = gateway
        self._store = store
        self._runs: dict[str, RunState] = {}

    def open_run(self, run_id: str, rule_sha256: str, input_snapshot_sha256: str, source_snapshot: SourceSnapshot | None = None) -> RunState:
        if source_snapshot is not None:
            validate_source_snapshot(source_snapshot)
            if (source_snapshot.run_id, source_snapshot.snapshot_sha256) != (run_id, input_snapshot_sha256):
                raise ContractError("source_snapshot_mismatch")
        existing = self._runs.get(run_id) or (self._store.load(run_id) if self._store else None)
        if existing:
            if (existing.rule_sha256, existing.input_snapshot_sha256) != (rule_sha256, input_snapshot_sha256):
                raise ContractError("run_contract_changed")
            if source_snapshot is not None and existing.source_snapshot != source_snapshot:
                raise ContractError("run_source_snapshot_changed")
            self._runs[run_id] = existing
            return existing
        state = RunState(run_id, rule_sha256, input_snapshot_sha256, source_snapshot)
        self._runs[run_id] = state
        self._save(state)
        return state

    def submit_analysis(self, bundle: AnalysisBundle, plan: WritePlan) -> None:
        validate_analysis(bundle)
        validate_write_plan(plan)
        state = self._runs.get(bundle.run_id)
        if not state:
            raise ContractError("run_not_open")
        if (bundle.rule_sha256, bundle.input_snapshot_sha256) != (state.rule_sha256, state.input_snapshot_sha256):
            raise ContractError("analysis_contract_mismatch")
        if (plan.record_id, plan.generation, plan.rule_sha256, plan.input_snapshot_sha256) != (
            bundle.record_id, bundle.generation, bundle.rule_sha256, bundle.input_snapshot_sha256
        ):
            raise ContractError("plan_analysis_mismatch")
        if plan.analysis_sha256 != bundle.artifact_sha256:
            raise ContractError("plan_analysis_sha_mismatch")
        if state.source_snapshot is not None and bundle.record_id not in state.source_snapshot.record_ids:
            raise ContractError("record_not_in_source_snapshot")
        old = state.plans.get(bundle.record_id)
        if old and old.generation > plan.generation:
            raise ContractError("generation_regression")
        state.plans[bundle.record_id] = plan
        self._save(state)

    def commit_stage(self, run_id: str, record_id: str, stage: Stage) -> StageReceipt:
        if stage not in (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT):
            raise ContractError("write_stage_required")
        state = self._runs.get(run_id)
        if not state or record_id not in state.plans:
            raise ContractError("plan_not_found")
        plan = state.plans[record_id]
        key = (record_id, plan.generation, stage)
        if key in state.receipts:
            return state.receipts[key]
        index = (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT).index(stage)
        previous = (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT)[index - 1] if index else None
        if previous and (record_id, plan.generation, previous) not in state.receipts:
            raise ContractError("previous_stage_unverified")
        receipt = self._gateway.commit(plan, stage)
        if receipt.run_id != run_id or receipt.record_id != record_id or receipt.generation != plan.generation:
            raise ContractError("receipt_identity_mismatch")
        validate_receipt(receipt)
        state.receipts[key] = receipt
        self._save(state)
        return receipt

    def status(self, run_id: str, record_id: str) -> dict[str, bool]:
        state = self._runs.get(run_id) or (self._store.load(run_id) if self._store else None)
        if not state:
            raise ContractError("run_not_open")
        plan = state.plans.get(record_id)
        if not plan:
            raise ContractError("plan_not_found")
        return {stage.value: (record_id, plan.generation, stage) in state.receipts for stage in (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT)}

    def _save(self, state: RunState) -> None:
        if self._store:
            self._store.save(state)


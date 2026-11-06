"""Fail-closed bridge from the verified v0.4.2 runtime to portable receipts.

This module is intentionally credential-free.  The private deployment injects
one legacy stage callable for each allowed remote stage.  A callable can only
advance the portable runner by returning a v0.4.2 readback that proves the
same record, stage and successful target-system verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from zhou_livecase.contracts import ContractError, RuntimePreflight, Stage, StageReceipt, WritePlan, validate_runtime_preflight


LegacyStageCallable = Callable[[WritePlan], Mapping[str, Any]]


_STAGE_NAMES = {
    Stage.STORAGE: "STORAGE_WRITE",
    Stage.CASE_WRITE: "CASE_WRITE",
    Stage.Q50_WRITE: "Q50_WRITE",
    Stage.SOURCE_CLOSEOUT: "SOURCE_WRITE",
}


def _readback_at(value: Mapping[str, Any]) -> str:
    for key in ("readback_at", "verified_at", "completed_at", "updated_at"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return datetime.now(timezone.utc).isoformat()


def _legacy_stage(value: Mapping[str, Any]) -> str:
    stage = value.get("stage") or value.get("stage_name")
    return str(stage or "").strip().upper()


@dataclass(frozen=True)
class LegacyStageAdapter:
    """One private v0.4.2 stage executor with strict receipt normalization."""

    stage: Stage
    execute: LegacyStageCallable

    def run(self, plan: WritePlan) -> dict[str, Any]:
        raw = dict(self.execute(plan))
        expected = _STAGE_NAMES[self.stage]
        if raw.get("verified") is not True:
            raise ContractError("v042_readback_unverified")
        if _legacy_stage(raw) != expected:
            raise ContractError("v042_stage_mismatch")
        for name, expected_value in (("record_id", plan.record_id), ("run_id", plan.run_id)):
            actual = raw.get(name)
            if actual not in (None, expected_value):
                raise ContractError(f"v042_identity_mismatch:{name}")
        raw["record_id"] = plan.record_id
        raw["run_id"] = plan.run_id
        raw["compatibility_runtime"] = "zhou_codex_single_window_v0.4.2"
        raw["readback_at"] = _readback_at(raw)
        return raw


class V042StageBridge:
    """ProductionGateway-compatible composition of existing v0.4.2 writers.

    This is the only supported migration path: adapters are supplied by the
    existing private runtime, not by an AI prompt, a Page, or release config.
    Missing adapter configuration fails before any remote call is attempted.
    """

    def __init__(
        self,
        *,
        storage: LegacyStageAdapter,
        case: LegacyStageAdapter,
        q50: LegacyStageAdapter,
        source: LegacyStageAdapter,
        preflight: RuntimePreflight,
    ) -> None:
        validate_runtime_preflight(preflight)
        self._preflight = preflight
        adapters = (storage, case, q50, source)
        expected = (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT)
        if tuple(adapter.stage for adapter in adapters) != expected:
            raise ContractError("v042_bridge_stage_configuration")
        self._adapters = dict(zip(expected, adapters, strict=True))

    def commit(self, plan: WritePlan, stage: Stage) -> StageReceipt:
        if plan.run_id != self._preflight.execution_id:
            raise ContractError("preflight_execution_mismatch")
        adapter = self._adapters.get(stage)
        if adapter is None:
            raise ContractError("unsupported_production_stage")
        readback = adapter.run(plan)
        return StageReceipt(
            schema="zhou-stage-receipt-v1",
            run_id=plan.run_id,
            record_id=plan.record_id,
            generation=plan.generation,
            stage=stage,
            idempotency_key=plan.idempotency_key,
            readback=readback,
            created_at=str(readback["readback_at"]),
        )

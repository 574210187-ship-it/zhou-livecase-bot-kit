from __future__ import annotations

from typing import Any, Protocol

from zhou_livecase.contracts import ContractError, RuntimePreflight, Stage, StageReceipt, WritePlan, validate_runtime_preflight


class StorageWriter(Protocol):
    def store_and_readback(self, plan: WritePlan) -> dict[str, Any]: ...


class CaseWriter(Protocol):
    def write_and_readback(self, plan: WritePlan) -> dict[str, Any]: ...


class Q50Writer(Protocol):
    def write_and_readback(self, plan: WritePlan) -> dict[str, Any]: ...


class SourceWriter(Protocol):
    def closeout_and_readback(self, plan: WritePlan) -> dict[str, Any]: ...


class ProductionGateway:
    """The only adapter composition allowed to perform production writes.

    Concrete COS/Feishu clients are injected by the private runtime.  This
    class deliberately accepts no access token, path, table ID, or arbitrary
    callback from an AI request; those belong in private deployment config.
    """

    def __init__(self, storage: StorageWriter, case: CaseWriter, q50: Q50Writer, source: SourceWriter, *, preflight: RuntimePreflight):
        validate_runtime_preflight(preflight)
        self._preflight = preflight
        self._writers = {
            Stage.STORAGE: storage.store_and_readback,
            Stage.CASE_WRITE: case.write_and_readback,
            Stage.Q50_WRITE: q50.write_and_readback,
            Stage.SOURCE_CLOSEOUT: source.closeout_and_readback,
        }

    def commit(self, plan: WritePlan, stage: Stage) -> StageReceipt:
        if plan.run_id != self._preflight.execution_id:
            raise ContractError("preflight_execution_mismatch")
        writer = self._writers.get(stage)
        if writer is None:
            raise ContractError("unsupported_production_stage")
        readback = writer(plan)
        if not isinstance(readback, dict) or readback.get("verified") is not True:
            raise ContractError("adapter_readback_unverified")
        return StageReceipt(
            schema="zhou-stage-receipt-v1",
            run_id=plan.run_id,
            record_id=plan.record_id,
            generation=plan.generation,
            stage=stage,
            idempotency_key=plan.idempotency_key,
            readback=readback,
            created_at=str(readback.get("readback_at", "")),
        )

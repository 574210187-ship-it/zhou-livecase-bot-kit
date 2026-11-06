from __future__ import annotations

from typing import Protocol

from zhou_livecase.contracts.models import AuditReport, ReworkOrder, Stage


class ReadOnlyGateway(Protocol):
    """Read-only target-system view. Must not expose create/update/delete methods."""

    def storage_verified(self, record_id: str) -> bool: ...
    def case_verified(self, record_id: str) -> bool: ...
    def q50_verified_globally(self, record_id: str) -> bool: ...
    def source_verified(self, record_id: str) -> bool: ...


class Auditor:
    """Independent checker. It never imports runner or changes target systems."""

    def __init__(self, gateway: ReadOnlyGateway, version: str = "auditor-v1"):
        self._gateway = gateway
        self.version = version

    def audit(self, run_id: str, record_id: str, generation: int) -> AuditReport:
        checks = {
            "storage": self._gateway.storage_verified(record_id),
            "case": self._gateway.case_verified(record_id),
            "q50_global": self._gateway.q50_verified_globally(record_id),
            "source": self._gateway.source_verified(record_id),
        }
        failed = next((name for name, passed in checks.items() if not passed), None)
        if failed is None:
            return AuditReport("zhou-audit-report-v1", run_id, record_id, generation, True, checks)
        restart = {
            "storage": Stage.STORAGE,
            "case": Stage.CASE_WRITE,
            "q50_global": Stage.Q50_WRITE,
            "source": Stage.SOURCE_CLOSEOUT,
        }[failed]
        order = ReworkOrder(
            schema="zhou-rework-order-v1",
            run_id=run_id,
            record_id=record_id,
            generation=generation,
            restart_stage=restart,
            error_code=f"audit_{failed}_failed",
            evidence={"checks": checks, "auditor_version": self.version},
        )
        return AuditReport("zhou-audit-report-v1", run_id, record_id, generation, False, checks, order)


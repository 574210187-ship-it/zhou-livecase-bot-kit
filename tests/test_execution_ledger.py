from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zhou_livecase.contracts import ContractError, RuntimePreflight, SourceSnapshot
from zhou_livecase.runner import ExecutionLedger


SHA = "a" * 64


def preflight(execution_id: str = "exec-1") -> RuntimePreflight:
    return RuntimePreflight(
        "zhou-runtime-preflight-v1",
        execution_id,
        "env-1",
        SHA,
        SHA,
        SHA,
        "zhou_livecase.production_entrypoint",
        "GPT-5.6 Luna",
        "high",
        "2026-11-06T00:00:00Z",
        {"storage": True, "case": True, "q50": True, "source": True},
        True,
    )


def snapshot(execution_id: str = "exec-1") -> SourceSnapshot:
    return SourceSnapshot("zhou-source-snapshot-v1", execution_id, "source", "2026-11-06T00:00:00Z", (SHA,), ("r1", "r2"), SHA)


class ExecutionLedgerTests(unittest.TestCase):
    def audit(self, execution_id: str = "exec-1", verified: tuple[str, ...] = ("r1",)) -> dict:
        return {
            "schema": "zhou-independent-audit-v1",
            "execution_id": execution_id,
            "source_snapshot_sha256": SHA,
            "audited_at": "2026-11-06T00:10:00Z",
            "auditor_version": "auditor-1",
            "passed": True,
            "verified_record_ids": list(verified),
            "failed_record_ids": [],
        }

    def test_start_persists_real_entrypoint_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = ExecutionLedger(Path(directory)).start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            self.assertTrue(state["entrypoint_started"])
            self.assertEqual(set(state["records"]), {"r1", "r2"})
            self.assertEqual(state["source_snapshot"]["snapshot_sha256"], SHA)

    def test_same_execution_is_idempotent_but_different_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ExecutionLedger(Path(directory))
            first = ledger.start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            second = ledger.start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            self.assertEqual(first["started_at"], second["started_at"])
            changed = SourceSnapshot(snapshot().schema, snapshot().run_id, snapshot().source_table, snapshot().captured_at, snapshot().page_sha256, ("r1",), SHA)
            with self.assertRaisesRegex(ContractError, "execution_id_reused_with_different_snapshot"):
                ledger.start(preflight=preflight(), run_id="exec-1", snapshot=changed)

    def test_success_requires_four_way_receipts_for_every_complete_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ExecutionLedger(Path(directory))
            ledger.start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            with self.assertRaisesRegex(ContractError, "complete_stage_receipts_incomplete"):
                ledger.record("exec-1", record_id="r1", status="complete", four_way_readback_verified=True, stage_receipts=[])

    def test_partial_result_is_not_success_and_cannot_be_silently_upgraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ExecutionLedger(Path(directory))
            ledger.start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            ledger.record("exec-1", record_id="r1", status="blocked_model", error_code="model_unavailable")
            ledger.record("exec-1", record_id="r2", status="closed_no_accept", stage_receipts=[{"stage": "source", "verified": True, "readback_id": "src-2"}])
            receipt = ledger.finish("exec-1", audit_summary=None)
            self.assertEqual(receipt.status, "partial")
            self.assertEqual(receipt.remaining_count, 1)
            self.assertEqual(ledger.read_receipt("exec-1").status, "partial")

    def test_success_has_conserved_counts_and_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ExecutionLedger(Path(directory))
            ledger.start(preflight=preflight(), run_id="exec-1", snapshot=snapshot())
            receipts = tuple({"stage": stage, "verified": True, "readback_id": f"{stage}-1"} for stage in ("storage", "case", "q50", "source"))
            ledger.record("exec-1", record_id="r1", status="complete", four_way_readback_verified=True, stage_receipts=list(receipts), remote_writes=4)
            ledger.record("exec-1", record_id="r2", status="closed_no_accept", stage_receipts=[{"stage": "source", "verified": True, "readback_id": "src-2"}])
            receipt = ledger.finish("exec-1", audit_summary=self.audit(verified=("r1",)))
            self.assertEqual(receipt.status, "success")
            self.assertEqual((receipt.candidate_count, receipt.terminal_count, receipt.complete_count, receipt.remaining_count), (2, 2, 1, 0))
            self.assertEqual(receipt.remote_writes, 4)


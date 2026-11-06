from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from zhou_livecase.auditor import Auditor, TargetSystemView
from zhou_livecase.contracts import AnalysisBundle, ContractError, RuntimePreflight, Stage, StageReceipt, WritePlan
from zhou_livecase.runner import JsonRunStore, ProductionGateway, Runner

SHA = "a" * 64


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[Stage] = []

    def commit(self, plan: WritePlan, stage: Stage) -> StageReceipt:
        self.calls.append(stage)
        data = {"verified": True}
        if stage == Stage.STORAGE:
            data.update({"storage_type": "feishu_attachment", "sha256": SHA, "fresh_download_sha256": SHA})
        if stage == Stage.Q50_WRITE:
            data.update({"case_business_key": "case-1", "target_id": "target-1", "score": 0.2, "level": "weak", "reason": "fixture", "evidence": "quote"})
        return StageReceipt("zhou-stage-receipt-v1", plan.run_id, plan.record_id, plan.generation, stage, plan.idempotency_key, data, "2026-11-01T00:00:00Z")


class ReadOnlyView:
    def __init__(self, **checks: bool) -> None:
        self.checks = checks

    def storage_verified(self, record_id: str) -> bool: return self.checks.get("storage", True)
    def case_verified(self, record_id: str) -> bool: return self.checks.get("case", True)
    def q50_verified_globally(self, record_id: str) -> bool: return self.checks.get("q50", True)
    def source_verified(self, record_id: str) -> bool: return self.checks.get("source", True)


class TargetReader:
    def __init__(self, **checks: bool) -> None: self.checks = checks
    def storage_download_sha_matches(self, record_id: str) -> bool: return self.checks.get("storage", True)
    def case_rows_match_business_keys(self, record_id: str) -> bool: return self.checks.get("case", True)
    def q50_rows_match_case_keys_globally(self, record_id: str) -> bool: return self.checks.get("q50", True)
    def source_row_has_verified_terminal_receipt(self, record_id: str) -> bool: return self.checks.get("source", True)


class StageWriter:
    def __init__(self, data: dict) -> None: self.data, self.calls = data, 0
    def store_and_readback(self, plan: WritePlan) -> dict: self.calls += 1; return self.data
    def write_and_readback(self, plan: WritePlan) -> dict: self.calls += 1; return self.data
    def closeout_and_readback(self, plan: WritePlan) -> dict: self.calls += 1; return self.data


def bundle() -> AnalysisBundle:
    return AnalysisBundle("zhou-analysis-bundle-v1", "run-1", "record-1", 0, SHA, SHA, SHA, ({"boundary_id": "b-1", "decision": "accept", "evidence_quote": "原文"},), "fixture", "2026-11-01T00:00:00Z")


def plan() -> WritePlan:
    return WritePlan("zhou-write-plan-v1", "run-1", "record-1", 0, SHA, SHA, SHA, "run-1:record-1:all:0", "feishu_attachment", ({"boundary_id": "b-1"},), ({"case_business_key": "case-1"},))


def preflight() -> RuntimePreflight:
    return RuntimePreflight("zhou-runtime-preflight-v1", "run-1", "env-1", SHA, SHA, SHA, "entrypoint", "GPT-5.6 Luna", "high", "2026-11-06T00:00:00Z", {"storage": True, "case": True, "q50": True, "source": True}, True)


class RunnerAuditorTests(unittest.TestCase):
    def test_runner_requires_order_and_is_idempotent(self) -> None:
        gateway = FakeGateway()
        runner = Runner(gateway)
        runner.open_run("run-1", SHA, SHA)
        runner.submit_analysis(bundle(), plan())
        with self.assertRaisesRegex(ContractError, "previous_stage_unverified"):
            runner.commit_stage("run-1", "record-1", Stage.Q50_WRITE)
        for stage in (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT):
            runner.commit_stage("run-1", "record-1", stage)
        runner.commit_stage("run-1", "record-1", Stage.SOURCE_CLOSEOUT)
        self.assertEqual(gateway.calls.count(Stage.SOURCE_CLOSEOUT), 1)

    def test_auditor_issues_smallest_rework_order(self) -> None:
        report = Auditor(ReadOnlyView(q50=False)).audit("run-1", "record-1", 0)
        self.assertFalse(report.passed)
        self.assertEqual(report.rework.restart_stage, Stage.Q50_WRITE)

    def test_auditor_is_complete_only_when_all_target_views_pass(self) -> None:
        self.assertTrue(Auditor(ReadOnlyView()).audit("run-1", "record-1", 0).passed)

    def test_restart_uses_persisted_receipts_but_new_generation_cannot_reuse_them(self) -> None:
        with TemporaryDirectory() as directory:
            gateway = FakeGateway()
            store = JsonRunStore(Path(directory))
            first = Runner(gateway, store)
            first.open_run("run-1", SHA, SHA)
            first.submit_analysis(bundle(), plan())
            first.commit_stage("run-1", "record-1", Stage.STORAGE)
            restarted = Runner(gateway, store)
            restarted.open_run("run-1", SHA, SHA)
            self.assertTrue(restarted.status("run-1", "record-1")["STORAGE"])
            newer_bundle = bundle().__class__(**{**bundle().__dict__, "generation": 1})
            newer_plan = plan().__class__(**{**plan().__dict__, "generation": 1, "idempotency_key": "run-1:record-1:all:1"})
            restarted.submit_analysis(newer_bundle, newer_plan)
            self.assertFalse(restarted.status("run-1", "record-1")["STORAGE"])
            restarted.commit_stage("run-1", "record-1", Stage.STORAGE)
            self.assertEqual(gateway.calls.count(Stage.STORAGE), 2)

    def test_production_gateway_only_returns_verified_stage_readback(self) -> None:
        storage = StageWriter({"verified": True, "storage_type": "feishu_attachment", "sha256": SHA, "fresh_download_sha256": SHA})
        case = StageWriter({"verified": True})
        q50 = StageWriter({"verified": True, "case_business_key": "case-1", "target_id": "target-1", "score": 0.2, "level": "weak", "reason": "fixture", "evidence": "quote"})
        source = StageWriter({"verified": True})
        gateway = ProductionGateway(storage, case, q50, source, preflight=preflight())
        self.assertEqual(gateway.commit(plan(), Stage.STORAGE).stage, Stage.STORAGE)
        self.assertEqual(storage.calls, 1)
        with self.assertRaisesRegex(ContractError, "adapter_readback_unverified"):
            ProductionGateway(StageWriter({"verified": False}), case, q50, source, preflight=preflight()).commit(plan(), Stage.STORAGE)

    def test_target_view_remains_read_only_and_uses_global_q50(self) -> None:
        report = Auditor(TargetSystemView(TargetReader(q50=False))).audit("run-1", "record-1", 0)
        self.assertEqual(report.rework.restart_stage, Stage.Q50_WRITE)


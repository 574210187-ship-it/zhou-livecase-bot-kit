from __future__ import annotations

import unittest

from zhou_livecase.compat import LegacyStageAdapter, V042StageBridge
from zhou_livecase.contracts import ContractError, RuntimePreflight, Stage, WritePlan


SHA = "a" * 64


def plan() -> WritePlan:
    return WritePlan(
        "zhou-write-plan-v1", "run-1", "record-1", 0, SHA, SHA, SHA,
        "run-1:record-1:all:0", "feishu_attachment", ({"boundary_id": "b-1"},),
        ({"case_business_key": "case-1"},),
    )


def preflight() -> RuntimePreflight:
    return RuntimePreflight("zhou-runtime-preflight-v1", "run-1", "env-1", SHA, SHA, SHA, "entrypoint", "GPT-5.6 Luna", "high", "2026-11-06T00:00:00Z", {"storage": True, "case": True, "q50": True, "source": True}, True)


def legacy(stage: str, extra: dict | None = None):
    data = {"verified": True, "stage": stage, "record_id": "record-1", "run_id": "run-1", "readback_at": "2026-11-02T00:00:00Z"}
    data.update(extra or {})
    return lambda _: data


class V042CompatibilityTests(unittest.TestCase):
    def bridge(self) -> V042StageBridge:
        return V042StageBridge(
            storage=LegacyStageAdapter(Stage.STORAGE, legacy("STORAGE_WRITE", {"storage_type": "feishu_attachment", "sha256": SHA, "fresh_download_sha256": SHA})),
            case=LegacyStageAdapter(Stage.CASE_WRITE, legacy("CASE_WRITE")),
            q50=LegacyStageAdapter(Stage.Q50_WRITE, legacy("Q50_WRITE", {"case_business_key": "case-1", "target_id": "target-1", "score": 0.1, "level": "weak", "reason": "fixture", "evidence": "quote"})),
            source=LegacyStageAdapter(Stage.SOURCE_CLOSEOUT, legacy("SOURCE_WRITE")),
            preflight=preflight(),
        )

    def test_normalizes_existing_verified_v042_readback(self) -> None:
        receipt = self.bridge().commit(plan(), Stage.STORAGE)
        self.assertEqual(receipt.stage, Stage.STORAGE)
        self.assertEqual(receipt.readback["compatibility_runtime"], "zhou_codex_single_window_v0.4.2")

    def test_refuses_unverified_or_wrong_stage_before_receipt(self) -> None:
        adapter = LegacyStageAdapter(Stage.STORAGE, legacy("CASE_WRITE"))
        with self.assertRaisesRegex(ContractError, "v042_stage_mismatch"):
            adapter.run(plan())
        adapter = LegacyStageAdapter(Stage.STORAGE, lambda _: {"verified": False, "stage": "STORAGE_WRITE"})
        with self.assertRaisesRegex(ContractError, "v042_readback_unverified"):
            adapter.run(plan())

    def test_refuses_cross_record_readback(self) -> None:
        adapter = LegacyStageAdapter(Stage.CASE_WRITE, legacy("CASE_WRITE", {"record_id": "other"}))
        with self.assertRaisesRegex(ContractError, "v042_identity_mismatch:record_id"):
            adapter.run(plan())

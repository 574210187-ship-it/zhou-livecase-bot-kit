from __future__ import annotations

import json
import unittest
from pathlib import Path

from zhou_livecase.auditor import Auditor
from zhou_livecase.contracts import ContractError, SourceSnapshot, Stage, validate_source_snapshot

from test_runner_auditor import ReadOnlyView, SHA, bundle, plan
from zhou_livecase.runner import Runner


ROOT = Path(__file__).resolve().parents[1]


class RegressionContractTests(unittest.TestCase):
    def snapshot(self, record_ids: tuple[str, ...] = ("record-1",)) -> SourceSnapshot:
        return SourceSnapshot("zhou-source-snapshot-v1", "run-1", "source-table", "2026-11-01T00:00:00Z", (SHA,), record_ids, SHA)

    def test_regression_manifest_has_all_historic_failure_classes(self) -> None:
        names = json.loads((ROOT / "fixtures/regressions/manifest.json").read_text(encoding="utf-8"))["fixtures"]
        self.assertEqual(len(names), 16)
        self.assertEqual(len(names), len(set(names)))

    def test_live_snapshot_rejects_duplicate_or_stale_record(self) -> None:
        with self.assertRaisesRegex(ContractError, "snapshot_duplicate_record_id"):
            validate_source_snapshot(self.snapshot(("record-1", "record-1")))
        runner = Runner(gateway=object())
        runner.open_run("run-1", SHA, SHA, self.snapshot())
        other = bundle().__class__(**{**bundle().__dict__, "record_id": "stale-record"})
        other_plan = plan().__class__(**{**plan().__dict__, "record_id": "stale-record"})
        with self.assertRaisesRegex(ContractError, "record_not_in_source_snapshot"):
            runner.submit_analysis(other, other_plan)

    def test_analysis_plan_hash_mismatch_is_rejected(self) -> None:
        runner = Runner(gateway=object())
        runner.open_run("run-1", SHA, SHA, self.snapshot())
        bad_plan = plan().__class__(**{**plan().__dict__, "analysis_sha256": "b" * 64})
        with self.assertRaisesRegex(ContractError, "plan_analysis_sha_mismatch"):
            runner.submit_analysis(bundle(), bad_plan)

    def test_auditor_uses_global_q50_view_and_never_imports_runner(self) -> None:
        report = Auditor(ReadOnlyView(q50=False)).audit("run-1", "record-1", 0)
        self.assertEqual(report.rework.restart_stage, Stage.Q50_WRITE)
        source = (ROOT / "src/zhou_livecase/auditor/service.py").read_text(encoding="utf-8")
        self.assertNotIn("zhou_livecase.runner", source)


from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from zhou_livecase.contracts import SourceSnapshot, Stage, StageReceipt, WritePlan

from .service import RunState


class JsonRunStore:
    """Per-run atomic JSON persistence without secrets or external credentials."""

    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, run_id: str) -> Path:
        if not run_id or "/" in run_id or "\\" in run_id:
            raise ValueError("invalid_run_id")
        return self.directory / f"{run_id}.json"

    def load(self, run_id: str) -> RunState | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot_payload = payload.get("source_snapshot")
        snapshot = SourceSnapshot(**{**snapshot_payload, "page_sha256": tuple(snapshot_payload["page_sha256"]), "record_ids": tuple(snapshot_payload["record_ids"])}) if snapshot_payload else None
        state = RunState(payload["run_id"], payload["rule_sha256"], payload["input_snapshot_sha256"], snapshot)
        state.plans = {
            record_id: WritePlan(**{**value, "case_rows": tuple(value["case_rows"]), "q50_rows": tuple(value["q50_rows"])})
            for record_id, value in payload["plans"].items()
        }
        for value in payload["receipts"]:
            receipt = StageReceipt(**{**value, "stage": Stage(value["stage"])})
            state.receipts[(receipt.record_id, receipt.generation, receipt.stage)] = receipt
        return state

    def save(self, state: RunState) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "zhou-run-state-v1",
            "run_id": state.run_id,
            "rule_sha256": state.rule_sha256,
            "input_snapshot_sha256": state.input_snapshot_sha256,
            "source_snapshot": asdict(state.source_snapshot) if state.source_snapshot else None,
            "plans": {record_id: asdict(plan) for record_id, plan in state.plans.items()},
            "receipts": [{**asdict(receipt), "stage": receipt.stage.value} for receipt in state.receipts.values()],
        }
        target = self._path(state.run_id)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        os.replace(temp, target)

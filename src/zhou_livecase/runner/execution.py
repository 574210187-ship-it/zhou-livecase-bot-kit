"""Durable production-session ledger.

This is the missing boundary between a cloud conversation and real work.  A
session is opened only after a live preflight and a full source snapshot.  The
ledger is append-oriented, uses one host lock, and can only emit ``success``
after every candidate is terminal and every ``complete`` record has four-way
target readback evidence.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from zhou_livecase.contracts import (
    ContractError,
    ExecutionReceipt,
    RecordExecutionResult,
    RuntimePreflight,
    SourceSnapshot,
    validate_execution_receipt,
    validate_audit_summary,
    validate_record_execution_result,
    validate_runtime_preflight,
    validate_source_snapshot,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    """Exclusive process lock; fail closed if the host cannot lock."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        try:
            import fcntl
        except ImportError as exc:  # pragma: no cover - Windows private runner uses its own lock
            raise ContractError("execution_lock_unsupported") from exc
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractError(f"execution_session_missing:{path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("execution_session_invalid")
    return value


class ExecutionLedger:
    """Single-writer, per-execution durable ledger for the private runtime."""

    def __init__(self, root: Path):
        self.root = root
        self.lock_path = root / ".execution.lock"

    def _path(self, execution_id: str) -> Path:
        if not execution_id or "/" in execution_id or "\\" in execution_id:
            raise ContractError("execution_id_invalid")
        return self.root / f"{execution_id}.json"

    def start(self, *, preflight: RuntimePreflight, run_id: str, snapshot: SourceSnapshot) -> dict[str, Any]:
        validate_runtime_preflight(preflight)
        validate_source_snapshot(snapshot)
        if preflight.execution_id != snapshot.run_id:
            raise ContractError("preflight_snapshot_execution_mismatch")
        if snapshot.run_id != run_id:
            raise ContractError("snapshot_run_mismatch")
        path = self._path(preflight.execution_id)
        with _lock(self.lock_path):
            if path.exists():
                existing = _read_json(path)
                existing_snapshot = existing.get("source_snapshot") or {}
                if (
                    existing.get("run_id") != run_id
                    or existing_snapshot.get("snapshot_sha256") != snapshot.snapshot_sha256
                    or tuple(existing_snapshot.get("record_ids") or ()) != tuple(snapshot.record_ids)
                    or tuple(existing_snapshot.get("page_sha256") or ()) != tuple(snapshot.page_sha256)
                ):
                    raise ContractError("execution_id_reused_with_different_snapshot")
                return existing
            records = {
                record_id: {
                    "record_id": record_id,
                    "status": "pending",
                    "stage_receipts": [],
                    "four_way_readback_verified": False,
                    "error_code": None,
                    "error_summary": None,
                    "updated_at": _now(),
                }
                for record_id in snapshot.record_ids
            }
            state = {
                "schema": "zhou-execution-session-v1",
                "execution_id": preflight.execution_id,
                "run_id": run_id,
                "environment_id": preflight.environment_id,
                "release_commit_sha256": preflight.release_commit_sha256,
                "release_zip_sha256": preflight.release_zip_sha256,
                "rule_sha256": preflight.rule_sha256,
                "entrypoint": preflight.entrypoint,
                "model": preflight.model,
                "reasoning": preflight.reasoning,
                "started_at": _now(),
                "finished_at": None,
                "entrypoint_started": True,
                "source_snapshot": asdict(snapshot),
                "records": records,
                "events": [{"at": _now(), "kind": "entrypoint_started", "execution_id": preflight.execution_id}],
                "remote_writes": 0,
                "target_readback_verified": False,
                "status": "running",
            }
            _write_json(path, state)
            return state

    def heartbeat(self, execution_id: str, *, event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        path = self._path(execution_id)
        with _lock(self.lock_path):
            state = _read_json(path)
            if state.get("status") != "running":
                raise ContractError("execution_not_running")
            state.setdefault("events", []).append({"at": _now(), "kind": event, "details": details or {}})
            _write_json(path, state)
            return state

    def record(
        self,
        execution_id: str,
        *,
        record_id: str,
        status: str,
        stage_receipts: list[dict[str, Any]] | None = None,
        four_way_readback_verified: bool = False,
        error_code: str | None = None,
        error_summary: str | None = None,
        remote_writes: int = 0,
    ) -> dict[str, Any]:
        result = RecordExecutionResult(
            record_id=record_id,
            status=status,
            stage_receipts=tuple(stage_receipts or ()),
            four_way_readback_verified=four_way_readback_verified,
            error_code=error_code,
            error_summary=error_summary,
        )
        validate_record_execution_result(result)
        path = self._path(execution_id)
        with _lock(self.lock_path):
            state = _read_json(path)
            if state.get("status") != "running":
                raise ContractError("execution_not_running")
            row = (state.get("records") or {}).get(record_id)
            if row is None:
                raise ContractError("record_not_in_execution_snapshot")
            old_status = str(row.get("status"))
            if old_status in {"complete", "closed_no_accept", "duplicate_processed", "cancelled"} and old_status != status:
                raise ContractError("terminal_record_rewrite")
            row.update({
                "status": status,
                "stage_receipts": list(result.stage_receipts),
                "four_way_readback_verified": result.four_way_readback_verified,
                "error_code": result.error_code,
                "error_summary": result.error_summary,
                "updated_at": _now(),
            })
            state["remote_writes"] = int(state.get("remote_writes", 0)) + int(remote_writes)
            state.setdefault("events", []).append({"at": _now(), "kind": "record_result", "record_id": record_id, "status": status})
            _write_json(path, state)
            return state

    def finish(
        self,
        execution_id: str,
        *,
        audit_summary: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> ExecutionReceipt:
        path = self._path(execution_id)
        with _lock(self.lock_path):
            state = _read_json(path)
            if state.get("status") != "running":
                raise ContractError("execution_already_finished")
            records = tuple(
                RecordExecutionResult(
                    record_id=rid,
                    status=str(row.get("status")),
                    stage_receipts=tuple(row.get("stage_receipts") or ()),
                    four_way_readback_verified=bool(row.get("four_way_readback_verified")),
                    error_code=row.get("error_code"),
                    error_summary=row.get("error_summary"),
                )
                for rid, row in sorted((state.get("records") or {}).items())
            )
            candidate_count = len(records)
            terminal_states = {"complete", "closed_no_accept", "duplicate_processed", "cancelled"}
            terminal_count = sum(item.status in terminal_states for item in records)
            complete_count = sum(item.status == "complete" for item in records)
            failed_count = sum(item.status in {"failed_final", "failed_retryable"} for item in records)
            remaining_count = candidate_count - terminal_count
            audit_errors = list(errors or ())
            complete_ids = {item.record_id for item in records if item.status == "complete"}
            audit_ok = False
            if audit_summary is not None:
                try:
                    validate_audit_summary(
                        audit_summary,
                        execution_id=execution_id,
                        source_snapshot_sha256=str(state["source_snapshot"]["snapshot_sha256"]),
                        complete_ids=complete_ids,
                    )
                    audit_ok = True
                except ContractError as exc:
                    audit_errors.append({"code": str(exc), "summary": "independent_target_audit_rejected"})
            else:
                audit_errors.append({"code": "target_audit_missing", "summary": "independent target-system readback is required before success"})
            if candidate_count == 0:
                status = "no_candidate"
            elif remaining_count == 0 and audit_ok and all(
                item.status != "complete" or item.four_way_readback_verified for item in records
            ):
                status = "success"
            elif any(item.status in {"failed_final", "failed_retryable"} for item in records):
                status = "failed"
            else:
                status = "partial"
            receipt = ExecutionReceipt(
                schema="zhou-execution-receipt-v1",
                execution_id=str(state["execution_id"]),
                run_id=str(state["run_id"]),
                environment_id=str(state["environment_id"]),
                release_commit_sha256=str(state["release_commit_sha256"]),
                release_zip_sha256=str(state["release_zip_sha256"]),
                rule_sha256=str(state["rule_sha256"]),
                source_snapshot_sha256=str(state["source_snapshot"]["snapshot_sha256"]),
                started_at=str(state["started_at"]),
                finished_at=_now(),
                status=status,
                candidate_count=candidate_count,
                terminal_count=terminal_count,
                complete_count=complete_count,
                failed_count=failed_count,
                remaining_count=remaining_count,
                remote_writes=int(state.get("remote_writes", 0)),
                entrypoint_started=bool(state.get("entrypoint_started")),
                target_readback_verified=audit_ok,
                records=records,
                errors=tuple(audit_errors),
            )
            validate_execution_receipt(receipt)
            state["status"] = receipt.status
            state["finished_at"] = receipt.finished_at
            state["target_readback_verified"] = receipt.target_readback_verified
            state["audit_summary"] = audit_summary
            state["execution_receipt"] = asdict(receipt)
            state.setdefault("events", []).append({"at": receipt.finished_at, "kind": "entrypoint_finished", "status": receipt.status})
            _write_json(path, state)
            _write_json(path.with_name(f"{execution_id}.receipt.json"), asdict(receipt))
            return receipt

    def read_receipt(self, execution_id: str) -> ExecutionReceipt:
        path = self._path(execution_id).with_name(f"{execution_id}.receipt.json")
        data = _read_json(path)
        records = tuple(RecordExecutionResult(**{
            **item,
            "stage_receipts": tuple(item.get("stage_receipts") or ()),
        }) for item in data.get("records") or ())
        receipt = ExecutionReceipt(**{**data, "records": records, "errors": tuple(data.get("errors") or ())})
        validate_execution_receipt(receipt)
        return receipt

"""Machine-facing production entrypoint.

The cloud worker must call this module for every run.  Natural-language thread
activity is not an entrypoint.  The private runtime builds the preflight from
its live environment, then calls ``start`` before any analysis or write.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from zhou_livecase.contracts import RuntimePreflight, SourceSnapshot
from zhou_livecase.runner import ExecutionLedger


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _preflight(path: Path) -> RuntimePreflight:
    return RuntimePreflight(**_json(path))


def _snapshot(path: Path) -> SourceSnapshot:
    raw = _json(path)
    raw["page_sha256"] = tuple(raw.get("page_sha256") or ())
    raw["record_ids"] = tuple(raw.get("record_ids") or ())
    return SourceSnapshot(**raw)


def _printable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="zhou-livecase fail-closed production session entrypoint")
    parser.add_argument("--ledger", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("--preflight", type=Path, required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--run-id", required=True)

    p = sub.add_parser("heartbeat")
    p.add_argument("--execution-id", required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--details", type=Path)

    p = sub.add_parser("record")
    p.add_argument("--execution-id", required=True)
    p.add_argument("--record-id", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--four-way-readback-verified", action="store_true")
    p.add_argument("--stage-receipts", type=Path)
    p.add_argument("--error-code")
    p.add_argument("--error-summary")
    p.add_argument("--remote-writes", type=int, default=0)

    p = sub.add_parser("finish")
    p.add_argument("--execution-id", required=True)
    p.add_argument("--audit-report", type=Path)
    p.add_argument("--errors", type=Path)

    p = sub.add_parser("receipt")
    p.add_argument("--execution-id", required=True)

    args = parser.parse_args(argv)
    ledger = ExecutionLedger(args.ledger)
    try:
        if args.command == "start":
            result = ledger.start(preflight=_preflight(args.preflight), run_id=args.run_id, snapshot=_snapshot(args.snapshot))
        elif args.command == "heartbeat":
            details = _json(args.details) if args.details else {}
            result = ledger.heartbeat(args.execution_id, event=args.event, details=details)
        elif args.command == "record":
            stage_receipts = []
            if args.stage_receipts:
                raw = json.loads(args.stage_receipts.read_text(encoding="utf-8"))
                stage_receipts = raw if isinstance(raw, list) else list(raw.get("stage_receipts") or ())
            result = ledger.record(
                args.execution_id,
                record_id=args.record_id,
                status=args.status,
                stage_receipts=stage_receipts,
                four_way_readback_verified=args.four_way_readback_verified,
                error_code=args.error_code,
                error_summary=args.error_summary,
                remote_writes=args.remote_writes,
            )
        elif args.command == "finish":
            errors = []
            if args.errors:
                raw = json.loads(args.errors.read_text(encoding="utf-8"))
                errors = raw if isinstance(raw, list) else list(raw.get("errors") or ())
            audit_report = _json(args.audit_report) if args.audit_report else None
            result = ledger.finish(args.execution_id, audit_summary=audit_report, errors=errors)
            result = _printable(result)
        else:
            result = ledger.read_receipt(args.execution_id)
            result = _printable(result)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

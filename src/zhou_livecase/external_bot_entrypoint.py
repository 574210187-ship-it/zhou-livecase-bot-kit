from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from .providers.capabilities import evaluate_profile, select_route
from .providers.delegated_chat import validate_delegated_chat_receipt
from .providers.human_readability import validate_visible_payload
from .providers.route_comparison import compare_routes


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def _emit(value: dict) -> int:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    passed = value.get("passed", value.get("ready", value.get("selected_route") is not None))
    return 0 if passed else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="External bot production preflight and quality gates")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--profile", type=Path, required=True)
    preflight.add_argument("--preferred", default="auto")

    visible = subparsers.add_parser("validate-visible")
    visible.add_argument("--input", type=Path, required=True)

    delegated = subparsers.add_parser("validate-delegated")
    delegated.add_argument("--receipt", type=Path, required=True)

    compare = subparsers.add_parser("compare-routes")
    compare.add_argument("--inline", type=Path, required=True)
    compare.add_argument("--delegated", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "preflight":
            return _emit(select_route(_load(args.profile), args.preferred))
        if args.command == "validate-visible":
            return _emit(validate_visible_payload(_load(args.input)))
        if args.command == "validate-delegated":
            return _emit(validate_delegated_chat_receipt(_load(args.receipt)))
        if args.command == "compare-routes":
            return _emit(compare_routes(_load(args.inline), _load(args.delegated)))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _emit({"schema": "zhou-external-bot-error-v1", "passed": False, "error": str(error)})
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())

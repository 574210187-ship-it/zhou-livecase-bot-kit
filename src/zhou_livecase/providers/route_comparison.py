from __future__ import annotations

import math
from typing import Any

from .capabilities import DELEGATED_ROUTE, INLINE_ROUTE


def _valid(metrics: dict[str, Any]) -> bool:
    attempted = metrics.get("records_attempted")
    completed = metrics.get("records_completed")
    return (
        metrics.get("schema") == "zhou-route-metrics-v1"
        and metrics.get("route") in {INLINE_ROUTE, DELEGATED_ROUTE}
        and isinstance(attempted, int)
        and attempted > 0
        and completed == attempted
        and metrics.get("quality_gate_passed") is True
        and metrics.get("independent_audit_passed") is True
        and metrics.get("unverified_remote_writes") == 0
        and metrics.get("cleanup_failures", 0) == 0
    )


def _score(metrics: dict[str, Any]) -> tuple[float, float, float, str]:
    seconds = float(metrics.get("wall_seconds") or math.inf)
    tokens = metrics.get("reported_tokens")
    token_score = float(tokens) if isinstance(tokens, (int, float)) and tokens >= 0 else math.inf
    retries = float(metrics.get("retries") or 0)
    return (seconds, token_score, retries, str(metrics["route"]))


def compare_routes(inline: dict[str, Any], delegated: dict[str, Any]) -> dict[str, Any]:
    """Correctness first, then elapsed time, then reported tokens."""

    if inline.get("route") != INLINE_ROUTE or delegated.get("route") != DELEGATED_ROUTE:
        raise ValueError("route_metric_pair_mismatch")
    candidates = [item for item in (inline, delegated) if _valid(item)]
    selected = min(candidates, key=_score)["route"] if candidates else None
    return {
        "schema": "zhou-route-comparison-v1",
        "selected_route": selected,
        "decision_order": ["quality_and_audit", "wall_seconds", "reported_tokens", "retries"],
        "routes": [
            {
                "route": item.get("route"),
                "eligible": _valid(item),
                "wall_seconds": item.get("wall_seconds"),
                "reported_tokens": item.get("reported_tokens"),
                "reported_tokens_known": isinstance(item.get("reported_tokens"), (int, float)),
                "retries": item.get("retries"),
            }
            for item in (inline, delegated)
        ],
    }

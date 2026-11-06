from __future__ import annotations

import unittest

from zhou_livecase.providers.capabilities import DELEGATED_ROUTE, INLINE_ROUTE
from zhou_livecase.providers.route_comparison import compare_routes


def metrics(route, **overrides):
    value = {
        "schema": "zhou-route-metrics-v1",
        "route": route,
        "records_attempted": 2,
        "records_completed": 2,
        "quality_gate_passed": True,
        "independent_audit_passed": True,
        "unverified_remote_writes": 0,
        "cleanup_failures": 0,
        "wall_seconds": 120,
        "reported_tokens": 1000,
        "retries": 0,
    }
    value.update(overrides)
    return value


class RouteComparisonTests(unittest.TestCase):
    def test_faster_valid_route_wins(self) -> None:
        result = compare_routes(metrics(INLINE_ROUTE), metrics(DELEGATED_ROUTE, wall_seconds=90, reported_tokens=2000))
        self.assertEqual(result["selected_route"], DELEGATED_ROUTE)

    def test_quality_failure_excludes_faster_route(self) -> None:
        result = compare_routes(
            metrics(INLINE_ROUTE, wall_seconds=180),
            metrics(DELEGATED_ROUTE, wall_seconds=20, quality_gate_passed=False),
        )
        self.assertEqual(result["selected_route"], INLINE_ROUTE)

    def test_missing_cleanup_excludes_delegated_route(self) -> None:
        result = compare_routes(metrics(INLINE_ROUTE), metrics(DELEGATED_ROUTE, cleanup_failures=1))
        self.assertEqual(result["selected_route"], INLINE_ROUTE)

    def test_no_valid_route_fails_closed(self) -> None:
        result = compare_routes(
            metrics(INLINE_ROUTE, records_completed=1),
            metrics(DELEGATED_ROUTE, independent_audit_passed=False),
        )
        self.assertIsNone(result["selected_route"])

    def test_route_pair_cannot_be_swapped_or_duplicated(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_metric_pair_mismatch"):
            compare_routes(metrics(DELEGATED_ROUTE), metrics(INLINE_ROUTE))


if __name__ == "__main__":
    unittest.main()

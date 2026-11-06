from __future__ import annotations

import unittest

from zhou_livecase.providers.capabilities import DELEGATED_ROUTE, INLINE_ROUTE, evaluate_profile, select_route


def profile(**overrides):
    capabilities = {
        "filesystem_read_write": True,
        "python_execution": True,
        "live_source_pagination": True,
        "private_runner_call": True,
        "private_auditor_call": True,
        "target_system_readback": True,
        "structured_analysis": True,
        "visible_browser_automation": True,
        "chatgpt_file_upload": True,
        "chatgpt_result_download": True,
        "chatgpt_conversation_cleanup": True,
    }
    capabilities.update(overrides)
    return {
        "schema": "zhou-bot-capability-profile-v1",
        "provider": "grok",
        "profile_id": "grok-canary",
        "capabilities": capabilities,
    }


class ExternalBotPreflightTests(unittest.TestCase):
    def test_full_profile_prefers_inline(self) -> None:
        result = select_route(profile())
        self.assertTrue(result["ready"])
        self.assertEqual(result["selected_route"], INLINE_ROUTE)
        self.assertFalse(result["secrets_present"])

    def test_delegated_can_run_when_inline_analysis_is_missing(self) -> None:
        result = select_route(profile(structured_analysis=False))
        self.assertEqual(result["selected_route"], DELEGATED_ROUTE)

    def test_missing_private_runner_fails_both_routes_with_authorization_request(self) -> None:
        result = evaluate_profile(profile(private_runner_call=False))
        self.assertTrue(all(not item["executable"] for item in result["routes"]))
        self.assertTrue(all(item["authorization_requests"] for item in result["routes"]))

    def test_preferred_route_fails_closed(self) -> None:
        result = select_route(profile(chatgpt_conversation_cleanup=False), DELEGATED_ROUTE)
        self.assertFalse(result["ready"])
        self.assertIsNone(result["selected_route"])

    def test_profile_rejects_secret_material(self) -> None:
        value = profile()
        value["api_token"] = "must-not-be-here"
        with self.assertRaisesRegex(ValueError, "contains_secret_material"):
            evaluate_profile(value)

    def test_capability_values_are_boolean_only(self) -> None:
        value = profile()
        value["capabilities"]["private_runner_call"] = "yes"
        with self.assertRaisesRegex(ValueError, "must_be_boolean"):
            evaluate_profile(value)


if __name__ == "__main__":
    unittest.main()

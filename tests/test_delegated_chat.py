from __future__ import annotations

import unittest

from zhou_livecase.providers.delegated_chat import validate_delegated_chat_receipt


SHA = "a" * 64


def receipt(**overrides):
    value = {
        "schema": "zhou-delegated-chat-receipt-v1",
        "record_id": "source-001",
        "conversation_id": "conversation-001",
        "input_sha256": "b" * 64,
        "output_sha256": SHA,
        "downloaded_sha256": SHA,
        "status": "completed",
        "started_at": "2026-11-06T10:00:00+08:00",
        "finished_at": "2026-11-06T10:05:00+08:00",
        "cleanup_method": "visible_ui",
        "delete_clicked": True,
        "refresh_absence_verified": True,
        "deleted_at": "2026-11-06T10:06:00+08:00",
        "hidden_api_used": False,
    }
    value.update(overrides)
    return value


class DelegatedChatTests(unittest.TestCase):
    def test_complete_visible_cleanup_passes(self) -> None:
        self.assertTrue(validate_delegated_chat_receipt(receipt())["passed"])

    def test_missing_cleanup_fails(self) -> None:
        result = validate_delegated_chat_receipt(receipt(delete_clicked=False, refresh_absence_verified=False))
        self.assertIn("delete_not_confirmed", result["issues"])
        self.assertIn("refresh_absence_not_verified", result["issues"])

    def test_hidden_api_is_forbidden(self) -> None:
        result = validate_delegated_chat_receipt(receipt(hidden_api_used=True))
        self.assertIn("hidden_api_forbidden", result["issues"])

    def test_download_sha_must_match(self) -> None:
        result = validate_delegated_chat_receipt(receipt(downloaded_sha256="c" * 64))
        self.assertIn("download_sha_mismatch", result["issues"])


if __name__ == "__main__":
    unittest.main()

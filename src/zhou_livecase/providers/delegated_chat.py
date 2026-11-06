from __future__ import annotations

import re
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_delegated_chat_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Require visible-UI deletion and refreshed absence proof per chat."""

    issues: list[str] = []
    if receipt.get("schema") != "zhou-delegated-chat-receipt-v1":
        issues.append("receipt_schema")
    for name in ("record_id", "conversation_id", "started_at", "finished_at", "deleted_at"):
        if not str(receipt.get(name) or "").strip():
            issues.append(f"missing:{name}")
    for name in ("input_sha256", "output_sha256", "downloaded_sha256"):
        if not SHA256.fullmatch(str(receipt.get(name) or "")):
            issues.append(f"invalid_sha256:{name}")
    if receipt.get("output_sha256") != receipt.get("downloaded_sha256"):
        issues.append("download_sha_mismatch")
    if receipt.get("status") != "completed":
        issues.append("generation_not_completed")
    if receipt.get("cleanup_method") != "visible_ui":
        issues.append("cleanup_not_visible_ui")
    if receipt.get("delete_clicked") is not True:
        issues.append("delete_not_confirmed")
    if receipt.get("refresh_absence_verified") is not True:
        issues.append("refresh_absence_not_verified")
    if receipt.get("hidden_api_used") is not False:
        issues.append("hidden_api_forbidden")
    return {
        "schema": "zhou-delegated-chat-validation-v1",
        "record_id": str(receipt.get("record_id") or ""),
        "conversation_id": str(receipt.get("conversation_id") or ""),
        "passed": not issues,
        "issues": issues,
    }

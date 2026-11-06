from __future__ import annotations

import re
from typing import Iterable

from .models import (
    AnalysisBundle,
    ExecutionReceipt,
    RecordExecutionResult,
    RuntimePreflight,
    SourceSnapshot,
    Stage,
    StageReceipt,
    WritePlan,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ContractError(ValueError):
    pass


def _sha(value: str, name: str) -> None:
    if not SHA256.fullmatch(value):
        raise ContractError(f"invalid_sha256:{name}")


def _ids(rows: Iterable[dict], field: str) -> None:
    seen: set[str] = set()
    for row in rows:
        value = row.get(field)
        if not isinstance(value, str) or not value:
            raise ContractError(f"missing:{field}")
        if value in seen:
            raise ContractError(f"duplicate:{field}:{value}")
        seen.add(value)


def validate_source_snapshot(snapshot: SourceSnapshot) -> None:
    if snapshot.schema != "zhou-source-snapshot-v1":
        raise ContractError("snapshot_schema")
    if not snapshot.run_id or not snapshot.source_table or not snapshot.captured_at:
        raise ContractError("snapshot_identity")
    if not snapshot.page_sha256 or not snapshot.record_ids:
        raise ContractError("snapshot_empty")
    for value in (*snapshot.page_sha256, snapshot.snapshot_sha256):
        _sha(value, "snapshot_sha256")
    if any(not isinstance(record_id, str) or not record_id for record_id in snapshot.record_ids):
        raise ContractError("snapshot_record_id")
    if len(set(snapshot.record_ids)) != len(snapshot.record_ids):
        raise ContractError("snapshot_duplicate_record_id")


def validate_runtime_preflight(preflight: RuntimePreflight) -> None:
    if preflight.schema != "zhou-runtime-preflight-v1":
        raise ContractError("preflight_schema")
    for name in ("execution_id", "environment_id", "entrypoint", "model", "reasoning", "captured_at"):
        if not str(getattr(preflight, name) or "").strip():
            raise ContractError(f"preflight_missing:{name}")
    if not GIT_COMMIT.fullmatch(preflight.release_commit_sha256) and not SHA256.fullmatch(preflight.release_commit_sha256):
        raise ContractError("invalid_release_commit_sha256")
    for name in ("release_zip_sha256", "rule_sha256"):
        _sha(getattr(preflight, name), name)
    required = {"storage", "case", "q50", "source"}
    if set(preflight.adapter_readiness) != required:
        raise ContractError("preflight_adapter_set")
    if not preflight.ready:
        raise ContractError("preflight_not_ready:" + ",".join(preflight.failures or ("unknown",)))
    if any(preflight.adapter_readiness[name] is not True for name in required):
        raise ContractError("preflight_adapter_not_ready")


TERMINAL_RECORD_STATUSES = {"complete", "closed_no_accept", "duplicate_processed", "cancelled"}
BLOCKED_RECORD_STATUSES = {
    "blocked_permission",
    "blocked_source",
    "blocked_model",
    "blocked_fee_gate",
    "review_pending",
    "failed_retryable",
    "failed_final",
}


def validate_record_execution_result(result: RecordExecutionResult) -> None:
    if not result.record_id.strip():
        raise ContractError("record_result_identity")
    if result.status not in TERMINAL_RECORD_STATUSES | BLOCKED_RECORD_STATUSES:
        raise ContractError("record_result_status")
    if result.status == "complete":
        if result.four_way_readback_verified is not True:
            raise ContractError("complete_without_four_way_readback")
        stages = {str(item.get("stage")) for item in result.stage_receipts}
        if stages != {"storage", "case", "q50", "source"}:
            raise ContractError("complete_stage_receipts_incomplete")
        for item in result.stage_receipts:
            if item.get("verified") is not True or not item.get("readback_id"):
                raise ContractError("complete_stage_receipt_unverified")
    if result.status in {"closed_no_accept", "duplicate_processed", "cancelled"}:
        source_receipts = [item for item in result.stage_receipts if item.get("stage") == "source"]
        if len(source_receipts) != 1 or source_receipts[0].get("verified") is not True or not source_receipts[0].get("readback_id"):
            raise ContractError("terminal_without_source_readback")
    if result.status in BLOCKED_RECORD_STATUSES and not result.error_code:
        raise ContractError("blocked_record_error_code_missing")


def validate_execution_receipt(receipt: ExecutionReceipt) -> None:
    if receipt.schema != "zhou-execution-receipt-v1":
        raise ContractError("execution_receipt_schema")
    for name in ("execution_id", "run_id", "environment_id", "source_snapshot_sha256", "started_at"):
        if not str(getattr(receipt, name) or "").strip():
            raise ContractError(f"execution_receipt_missing:{name}")
    for name in ("release_commit_sha256", "release_zip_sha256", "rule_sha256", "source_snapshot_sha256"):
        _sha(getattr(receipt, name), name)
    if receipt.status not in {"running", "success", "partial", "failed", "no_candidate"}:
        raise ContractError("execution_receipt_status")
    if receipt.candidate_count != len(receipt.records):
        raise ContractError("execution_candidate_count_mismatch")
    seen: set[str] = set()
    for result in receipt.records:
        validate_record_execution_result(result)
        if result.record_id in seen:
            raise ContractError("execution_duplicate_record")
        seen.add(result.record_id)
    terminal = sum(item.status in TERMINAL_RECORD_STATUSES for item in receipt.records)
    complete = sum(item.status == "complete" for item in receipt.records)
    failed = sum(item.status in {"failed_final", "failed_retryable"} for item in receipt.records)
    remaining = receipt.candidate_count - terminal
    if (receipt.terminal_count, receipt.complete_count, receipt.failed_count, receipt.remaining_count) != (
        terminal,
        complete,
        failed,
        remaining,
    ):
        raise ContractError("execution_counts_not_conserved")
    if receipt.status == "success":
        if not receipt.finished_at or not receipt.entrypoint_started:
            raise ContractError("success_without_entrypoint_or_finish")
        if receipt.remaining_count != 0 or receipt.target_readback_verified is not True:
            raise ContractError("success_without_full_readback")
    if receipt.status == "no_candidate" and receipt.candidate_count != 0:
        raise ContractError("no_candidate_count_mismatch")


def validate_audit_summary(summary: dict, *, execution_id: str, source_snapshot_sha256: str, complete_ids: set[str]) -> None:
    """Validate the independent full-target audit required for success."""

    if summary.get("schema") != "zhou-independent-audit-v1":
        raise ContractError("audit_summary_schema")
    if summary.get("execution_id") != execution_id:
        raise ContractError("audit_summary_execution_mismatch")
    if summary.get("source_snapshot_sha256") != source_snapshot_sha256:
        raise ContractError("audit_summary_snapshot_mismatch")
    if summary.get("passed") is not True:
        raise ContractError("audit_summary_not_passed")
    if not str(summary.get("auditor_version") or "").strip() or not str(summary.get("audited_at") or "").strip():
        raise ContractError("audit_summary_identity_missing")
    verified = set(summary.get("verified_record_ids") or ())
    failed = set(summary.get("failed_record_ids") or ())
    if failed:
        raise ContractError("audit_summary_failed_records")
    if verified != complete_ids:
        raise ContractError("audit_summary_record_set_mismatch")


def validate_analysis(bundle: AnalysisBundle) -> None:
    if bundle.schema != "zhou-analysis-bundle-v1":
        raise ContractError("analysis_schema")
    if not bundle.run_id or not bundle.record_id or bundle.generation < 0:
        raise ContractError("analysis_identity")
    for name in ("rule_sha256", "input_snapshot_sha256", "artifact_sha256"):
        _sha(getattr(bundle, name), name)
    if not bundle.boundaries:
        raise ContractError("analysis_boundaries_empty")
    _ids(bundle.boundaries, "boundary_id")
    for boundary in bundle.boundaries:
        if boundary.get("decision") not in {"accept", "review", "reject"}:
            raise ContractError("analysis_decision")
        quote = boundary.get("evidence_quote")
        if not isinstance(quote, str) or not quote.strip():
            raise ContractError("analysis_evidence_quote")


def validate_write_plan(plan: WritePlan) -> None:
    if plan.schema != "zhou-write-plan-v1":
        raise ContractError("plan_schema")
    if not plan.idempotency_key.endswith(f":{plan.generation}"):
        raise ContractError("plan_idempotency_key")
    for name in ("rule_sha256", "input_snapshot_sha256", "analysis_sha256"):
        _sha(getattr(plan, name), name)
    if plan.storage_policy not in {"cos_required", "feishu_attachment"}:
        raise ContractError("plan_storage_policy")
    _ids(plan.case_rows, "boundary_id")
    _ids(plan.q50_rows, "case_business_key")
    if not plan.case_rows:
        raise ContractError("plan_case_rows_empty")
    if len(plan.case_rows) != len(plan.q50_rows):
        raise ContractError("plan_case_q50_count_mismatch")


def validate_receipt(receipt: StageReceipt) -> None:
    if receipt.schema != "zhou-stage-receipt-v1":
        raise ContractError("receipt_schema")
    if receipt.stage not in {Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT}:
        raise ContractError("receipt_stage")
    if not receipt.idempotency_key.endswith(f":{receipt.generation}"):
        raise ContractError("receipt_idempotency_key")
    if receipt.readback.get("verified") is not True:
        raise ContractError("receipt_readback_unverified")
    if receipt.stage == Stage.STORAGE:
        storage_type = receipt.readback.get("storage_type")
        if storage_type not in {"cos", "feishu_attachment"}:
            raise ContractError("receipt_storage_type")
        if receipt.readback.get("sha256") != receipt.readback.get("fresh_download_sha256"):
            raise ContractError("receipt_storage_sha_mismatch")
    if receipt.stage == Stage.Q50_WRITE:
        required = ("case_business_key", "target_id", "score", "level", "reason", "evidence")
        missing = [name for name in required if receipt.readback.get(name) in (None, "")]
        if missing:
            raise ContractError("receipt_q50_incomplete:" + ",".join(missing))


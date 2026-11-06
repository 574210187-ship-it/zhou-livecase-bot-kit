from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Stage(str, Enum):
    DISCOVER = "DISCOVER"
    SOURCE_VERIFY = "SOURCE_VERIFY"
    ANALYZE = "ANALYZE"
    CONTENT_GATE = "CONTENT_GATE"
    REVIEW_OR_APPROVE = "REVIEW_OR_APPROVE"
    STORAGE = "STORAGE"
    CASE_WRITE = "CASE_WRITE"
    Q50_WRITE = "Q50_WRITE"
    SOURCE_CLOSEOUT = "SOURCE_CLOSEOUT"
    FINAL_AUDIT = "FINAL_AUDIT"
    COMPLETED = "COMPLETED"


WRITE_STAGES = (Stage.STORAGE, Stage.CASE_WRITE, Stage.Q50_WRITE, Stage.SOURCE_CLOSEOUT)
STAGE_ORDER = (
    Stage.DISCOVER,
    Stage.SOURCE_VERIFY,
    Stage.ANALYZE,
    Stage.CONTENT_GATE,
    Stage.REVIEW_OR_APPROVE,
    *WRITE_STAGES,
    Stage.FINAL_AUDIT,
    Stage.COMPLETED,
)


@dataclass(frozen=True)
class SourceSnapshot:
    """Immutable, paginated source-table evidence used by one run.

    A runner must never use a stale local queue as its discovery truth.  The
    snapshot pins the source-table query, every page digest, and the record
    identifiers that were actually discovered at run start.
    """

    schema: str
    run_id: str
    source_table: str
    captured_at: str
    page_sha256: tuple[str, ...]
    record_ids: tuple[str, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class RuntimePreflight:
    """Non-sensitive proof that the production entrypoint is actually usable.

    A cloud conversation, an existing environment, or a saved prompt is not a
    runtime proof.  The private deployment must construct this object from the
    live environment and injected adapters immediately before opening a run.
    """

    schema: str
    execution_id: str
    environment_id: str
    release_commit_sha256: str
    release_zip_sha256: str
    rule_sha256: str
    entrypoint: str
    model: str
    reasoning: str
    captured_at: str
    adapter_readiness: dict[str, bool]
    ready: bool
    failures: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecordExecutionResult:
    """One source record's terminal evidence, never just a task label."""

    record_id: str
    status: str
    stage_receipts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    four_way_readback_verified: bool = False
    error_code: str | None = None
    error_summary: str | None = None


@dataclass(frozen=True)
class ExecutionReceipt:
    """Authoritative run result written only by the production entrypoint."""

    schema: str
    execution_id: str
    run_id: str
    environment_id: str
    release_commit_sha256: str
    release_zip_sha256: str
    rule_sha256: str
    source_snapshot_sha256: str
    started_at: str
    finished_at: str | None
    status: str
    candidate_count: int
    terminal_count: int
    complete_count: int
    failed_count: int
    remaining_count: int
    remote_writes: int
    entrypoint_started: bool
    target_readback_verified: bool
    records: tuple[RecordExecutionResult, ...] = field(default_factory=tuple)
    errors: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AnalysisBundle:
    schema: str
    run_id: str
    record_id: str
    generation: int
    rule_sha256: str
    input_snapshot_sha256: str
    artifact_sha256: str
    boundaries: tuple[dict[str, Any], ...]
    model: str
    created_at: str


@dataclass(frozen=True)
class WritePlan:
    schema: str
    run_id: str
    record_id: str
    generation: int
    rule_sha256: str
    input_snapshot_sha256: str
    analysis_sha256: str
    idempotency_key: str
    storage_policy: str
    case_rows: tuple[dict[str, Any], ...]
    q50_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class StageReceipt:
    schema: str
    run_id: str
    record_id: str
    generation: int
    stage: Stage
    idempotency_key: str
    readback: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class ReworkOrder:
    schema: str
    run_id: str
    record_id: str
    generation: int
    restart_stage: Stage
    error_code: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class AuditReport:
    schema: str
    run_id: str
    record_id: str
    generation: int
    passed: bool
    checks: dict[str, bool]
    rework: ReworkOrder | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


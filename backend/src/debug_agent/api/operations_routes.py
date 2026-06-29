from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field


class RuntimePathStatus(BaseModel):
    name: str
    label: str
    path: str
    exists: bool
    is_directory: bool
    writable: bool


class RuntimeConfigSummary(BaseModel):
    environment: str
    database_url: str
    database_kind: str
    database_path: str
    artifact_root: str
    artifact_retention_days: int
    report_base_url: str
    auto_writeback_enabled: bool
    queue_max_concurrency: int
    retry_max_attempts: int
    stale_running_job_seconds: int
    require_trusted_actor: bool
    enable_fixture_fallback: bool
    usage_budget_units: float
    enforce_usage_budget: bool
    lark_configured: bool
    lark_connector_mode: str
    lark_identity: str
    lark_profile: str
    lark_event_mode: Literal["webhook", "long_connection"]
    lark_bot_verification_configured: bool
    lark_bot_encrypt_configured: bool
    worker_running: bool
    worker_completion_hook_enabled: bool


class ProductionReadinessCheck(BaseModel):
    key: str
    label: str
    status: Literal["ok", "warning", "critical"]
    detail: str
    action: str


class ProductionReadinessResponse(BaseModel):
    generated_at: str
    level: Literal["healthy", "degraded", "critical"]
    config: RuntimeConfigSummary
    paths: list[RuntimePathStatus]
    checks: list[ProductionReadinessCheck]
    export_urls: dict[str, str]


class ArtifactRetentionFileSample(BaseModel):
    relative_path: str
    size_bytes: int
    modified_at: str
    age_days: float


class ArtifactRetentionStatus(BaseModel):
    generated_at: str
    artifact_root: str
    scan_root: str
    retention_days: int
    total_file_count: int
    total_size_bytes: int
    eligible_file_count: int
    eligible_size_bytes: int
    oldest_modified_at: str
    newest_modified_at: str
    eligible_samples: list[ArtifactRetentionFileSample]
    action: str


class ArtifactRetentionCleanupRequest(BaseModel):
    actor: str = ""
    dry_run: bool = True
    confirmation: str = ""
    limit: int = Field(default=500, ge=1, le=5_000)


class ArtifactRetentionCleanupResponse(BaseModel):
    actor: str
    dry_run: bool
    confirmation_required: bool
    confirmation_phrase: str
    deleted_file_count: int
    deleted_size_bytes: int
    deleted_samples: list[ArtifactRetentionFileSample]
    status_after: ArtifactRetentionStatus
    message: str


class PilotGateThresholds(BaseModel):
    min_completed_jobs: int
    min_success_rate: float
    max_p95_duration_ms: int
    max_estimated_cost_units: float
    max_model_call_errors: int
    max_writeback_failed: int
    max_lark_operation_failures: int


class PilotGateBatchEvidence(BaseModel):
    compared_batch_count: int
    completed_jobs: int
    best_batch_id: str
    best_success_rate: float
    best_p95_duration_ms: int
    best_estimated_cost_units: float
    best_quality_score: float
    best_efficiency_score: float


class PilotGateCheck(BaseModel):
    key: str
    label: str
    status: Literal["passed", "warning", "failed"]
    detail: str
    action: str


class PilotGateResponse(BaseModel):
    generated_at: str
    status: Literal["passed", "warning", "failed"]
    thresholds: PilotGateThresholds
    batch_evidence: PilotGateBatchEvidence
    checks: list[PilotGateCheck]
    comparison: Any
    export_urls: dict[str, str]


def build_operations_router(
    *,
    readiness: Callable[[], ProductionReadinessResponse],
    artifact_retention: Callable[[int], ArtifactRetentionStatus],
    cleanup_artifact_retention: Callable[
        [ArtifactRetentionCleanupRequest], ArtifactRetentionCleanupResponse
    ],
    pilot_gate: Callable[
        [int, int, float, int, float | None, int, int, int], PilotGateResponse
    ],
    export_debug_jobs: Callable[
        [str | None, str | None, int, int, Literal["created_at_asc", "created_at_desc"]],
        Response,
    ],
    export_support_bundle: Callable[[int], Response],
    export_database_backup: Callable[[], Response],
) -> APIRouter:
    router = APIRouter()

    @router.get("/operations/readiness")
    @router.get("/api/operations/readiness")
    def get_operations_readiness() -> ProductionReadinessResponse:
        return readiness()

    @router.get("/operations/artifact-retention")
    @router.get("/api/operations/artifact-retention")
    def get_artifact_retention_status(
        limit: int = Query(default=20, ge=0, le=200),
    ) -> ArtifactRetentionStatus:
        return artifact_retention(limit)

    @router.post("/operations/artifact-retention/cleanup")
    @router.post("/api/operations/artifact-retention/cleanup")
    def cleanup_artifact_retention_route(
        request: ArtifactRetentionCleanupRequest,
    ) -> ArtifactRetentionCleanupResponse:
        return cleanup_artifact_retention(request)

    @router.get("/operations/pilot-gate")
    @router.get("/api/operations/pilot-gate")
    def get_pilot_gate(
        limit: int = Query(default=5, ge=2, le=10),
        min_completed_jobs: int = Query(default=20, ge=1, le=10_000),
        min_success_rate: float = Query(default=0.8, ge=0, le=1),
        max_p95_duration_ms: int = Query(default=12_000, ge=1, le=3_600_000),
        max_estimated_cost_units: float | None = Query(default=None, ge=0),
        max_model_call_errors: int = Query(default=0, ge=0, le=10_000),
        max_writeback_failed: int = Query(default=0, ge=0, le=10_000),
        max_lark_operation_failures: int = Query(default=0, ge=0, le=10_000),
    ) -> PilotGateResponse:
        return pilot_gate(
            limit,
            min_completed_jobs,
            min_success_rate,
            max_p95_duration_ms,
            max_estimated_cost_units,
            max_model_call_errors,
            max_writeback_failed,
            max_lark_operation_failures,
        )

    @router.get("/exports/debug-jobs.zip")
    @router.get("/api/exports/debug-jobs.zip")
    def export_debug_jobs_zip(
        job_ids: str | None = None,
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        sort: Literal["created_at_asc", "created_at_desc"] = "created_at_desc",
    ) -> Response:
        return export_debug_jobs(job_ids, status, limit, offset, sort)

    @router.get("/operations/support-bundle.zip")
    @router.get("/api/operations/support-bundle.zip")
    def export_operations_support_bundle(
        audit_limit: int = Query(default=100, ge=0, le=500),
    ) -> Response:
        return export_support_bundle(audit_limit)

    @router.get("/operations/database-backup.zip")
    @router.get("/api/operations/database-backup.zip")
    def export_database_backup_zip() -> Response:
        return export_database_backup()

    return router

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from debug_agent.imports.csv_cases import CsvRejectedRow
from debug_agent.imports.spreadsheet_rows import SpreadsheetRejectedRow
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.jobs.service import RetryRecommendationDetail, SubmittedDebugJob
from debug_agent.jobs.worker import AsyncJobWorkerStatus
from debug_agent.lark.connector import LARK_PERMISSION_CONSOLE_URL
from debug_agent.models.config import AgentModelConfig, AgentModelRuntimeConfig, ModelCatalogOption
from debug_agent.storage.repository import (
    DebugBatch,
    DebugJobAttempt,
    HumanHandoffStatus,
    LarkOperationAudit,
    RecommendedActionStatus,
    RecommendedActionStatusEvent,
    RecommendedActionVerification,
    SpreadsheetWritebackAudit,
    StrategyFollowUpJob,
    TargetedProbeJob,
)


class DebugJobStatus(BaseModel):
    job_id: str
    case_id: str
    artifact_group_id: str
    status: str
    created_at: str
    updated_at: str
    attempt_count: int
    max_attempts: int
    remaining_attempts: int
    will_retry: bool
    retry_recommendation: str
    retry_recommendation_detail: RetryRecommendationDetail
    error_message: str | None
    evidence_ids: list[str]
    evidence_error_counts: dict[str, int]
    spreadsheet_writeback_audit: "SpreadsheetWritebackAuditSummary | None" = None


class DebugRunStageResponse(BaseModel):
    job_id: str
    stage: str
    status: str
    input: dict[str, object]
    output: dict[str, object]
    failure_reason: str
    retryable: bool
    attempt_count: int
    created_at: str
    updated_at: str


class DebugRunStageListResponse(BaseModel):
    stages: list[DebugRunStageResponse]


class EvidenceLedgerRecord(BaseModel):
    job_id: str
    evidence_id: str
    step_name: str
    prompt: dict[str, object]
    enhanced_constraints: dict[str, object]
    raw_output: str
    parsed_result: dict[str, object]
    judge_version: str
    score_delta: dict[str, object]
    artifact_links: list[dict[str, object]]


class EvidenceLedgerResponse(BaseModel):
    records: list[EvidenceLedgerRecord]


class SpreadsheetWritebackAuditSummary(BaseModel):
    status: str
    row_id: str
    report_url: str
    error_message: str
    updated_at: str


class DebugJobListResponse(BaseModel):
    jobs: list[DebugJobStatus]
    total_count: int


class BatchDebugJobRequest(BaseModel):
    case_ids: list[str]
    baseline_trials: int = Field(default=5, ge=0, le=5)
    max_concurrency: int = Field(default=1, ge=1, le=20)
    max_attempts: int = Field(default=2, ge=1, le=10)
    agent_model_config: AgentModelConfig | None = None


class BatchDebugJobResponse(BaseModel):
    batch_id: str
    batch: "DebugBatchProgressResponse"
    jobs: list[SubmittedDebugJob]
    rejected_case_ids: list[str]


class DebugBatchEvaluationSummary(BaseModel):
    row_count: int
    created_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    running_jobs: int
    success_rate: float
    failure_rate: float
    average_duration_ms: float
    p50_duration_ms: int
    p95_duration_ms: int
    max_duration_ms: int
    retry_scheduled_count: int
    model_call_count: int
    model_call_errors: int
    estimated_cost_units: float
    writeback_succeeded: int
    writeback_failed: int
    writeback_skipped: int
    speed_label: str
    cost_label: str
    stability_label: str
    trust_label: str
    comparison_summary: str


class DebugBatchComparisonItem(BaseModel):
    batch_id: str
    status: str
    total_jobs: int
    model_profile: str
    model_runner_model: str
    model_runner_locked: bool
    thinking_enabled_roles: list[str]
    success_rate: float
    p95_duration_ms: int
    estimated_cost_units: float
    model_call_errors: int
    writeback_failed: int
    quality_score: float
    efficiency_score: float
    summary: str


class DebugBatchComparisonResponse(BaseModel):
    generated_at: str
    batch_ids: list[str]
    items: list[DebugBatchComparisonItem]
    best_batch_id: str
    summary: str
    export_url: str


class DebugBatchProgressResponse(BaseModel):
    batch: DebugBatch
    status_counts: dict[str, int]
    failure_types: dict[str, int]
    failure_stages: dict[str, int]
    metrics: dict[str, int | float]
    agent_metrics: dict[str, dict[str, int | float]]
    evaluation_summary: DebugBatchEvaluationSummary
    progress_percent: float
    pending_count: int
    running_count: int
    completed_count: int
    failed_count: int
    recent_jobs: list[DebugJobStatus] = Field(default_factory=list)
    recent_attempts: list[DebugJobAttempt] = Field(default_factory=list)


class DebugBatchListResponse(BaseModel):
    batches: list[DebugBatchProgressResponse]


class ModelCatalogResponse(BaseModel):
    runtime: AgentModelRuntimeConfig
    agent_roles: list[dict[str, object]]
    debug_stages: list[dict[str, object]]
    live_models: list[ModelCatalogOption]
    live_model_count: int
    live_probe_error: str = ""


class AgentModelConnectionTestRequest(BaseModel):
    provider: Literal["ark", "api"] = "ark"
    base_url: str
    api_key: str = ""
    model_id: str = ""


class AgentModelConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    model_count: int = 0
    model_found: bool = False
    credential_ref: str = ""


class JsonlImportRequest(BaseModel):
    jsonl: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class JsonlRejectedLine(BaseModel):
    line_number: int
    error_message: str


class JsonlImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_lines: list[JsonlRejectedLine]


class CsvImportRequest(BaseModel):
    csv_text: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class CsvImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_rows: list[CsvRejectedRow]


class SpreadsheetRowImportRequest(BaseModel):
    rows: list[dict[str, object]]
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class SpreadsheetImportedRowResponse(BaseModel):
    sheet_row_id: str
    case_id: str


class SpreadsheetRowImportResponse(BaseModel):
    imported_case_ids: list[str]
    imported_rows: list[SpreadsheetImportedRowResponse]
    jobs: list[SubmittedDebugJob]
    rejected_rows: list[SpreadsheetRejectedRow]


class LarkAuthSessionRequest(BaseModel):
    identity: Literal["bot", "user"] = "user"
    profile: str = ""
    scopes: list[str] = Field(default_factory=list)
    redirect_url: str = ""
    actor: str = ""
    note: str = ""
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class LarkAuthSessionCompleteRequest(BaseModel):
    actor: str = ""
    note: str = ""


class RecommendedActionStatusRequest(BaseModel):
    status: Literal["pending", "accepted", "rejected", "applied"]
    actor: str = ""
    note: str = ""


class RecommendedActionVerificationRequest(BaseModel):
    actor: str = ""
    note: str = ""


class StrategyFollowUpJobRequest(BaseModel):
    actor: str = ""
    note: str = ""


class TargetedProbeJobRequest(BaseModel):
    actor: str = ""
    note: str = ""


class AutoDebugClosureRequest(BaseModel):
    actor: str = ""
    note: str = ""
    writeback: bool = False
    report_url: str = ""
    submit_controlled_probes: bool = False


class AutoDebugClosureReportResponse(BaseModel):
    source_job_id: str
    closure: AutoDebugClosureResult
    markdown: str
    report_artifact_url: str


class HumanHandoffStatusRequest(BaseModel):
    status: Literal["pending", "acknowledged", "in_progress", "resolved", "wont_fix"]
    actor: str = ""
    note: str = ""


class RecommendedActionVerificationResponse(RecommendedActionVerification):
    verification_job: SubmittedDebugJob


class StrategyFollowUpJobResponse(StrategyFollowUpJob):
    follow_up_job: SubmittedDebugJob


class TargetedProbeJobResponse(TargetedProbeJob):
    probe_job: SubmittedDebugJob


class TargetedProbeJobWithOutcome(TargetedProbeJob):
    outcome: Literal["pending", "target_cleared", "target_still_failing", "inconclusive"]
    success_rate: float
    summary: str
    escalation: str


class StrategyFollowUpJobWithOutcome(StrategyFollowUpJob):
    outcome: Literal["pending", "passed_stop_condition", "needs_escalation", "inconclusive"]
    success_rate: float
    summary: str
    escalation: str


class StrategyFollowUpJobListResponse(BaseModel):
    follow_ups: list[StrategyFollowUpJobWithOutcome] = Field(default_factory=list)


class TargetedProbeJobListResponse(BaseModel):
    probes: list[TargetedProbeJobWithOutcome] = Field(default_factory=list)


class HumanHandoffStatusListResponse(BaseModel):
    statuses: list[HumanHandoffStatus] = Field(default_factory=list)


class RecommendedActionVerificationResult(BaseModel):
    job_id: str
    action_index: int
    verification_job_id: str
    result: Literal["pending", "resolved", "not_resolved", "regressed", "inconclusive"]
    source_success_rate: float
    verification_success_rate: float
    source_root_cause: str
    verification_root_cause: str
    summary: str


class ActionQueueItemResponse(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    priority: str
    state: str
    state_label: str
    source: str
    source_ref: str
    owner: str
    status: str
    status_updated_at: str
    verification_job_id: str
    verification_result: str
    verification_summary: str
    writeback_status: str
    writeback_row_id: str
    writeback_report_url: str
    evidence_ids: str
    artifact_ids: str
    trace_refs: str
    available_operations: list[str] = Field(default_factory=list)
    next_operation: str


class ActionQueueResponse(BaseModel):
    job_id: str
    summary: dict[str, int]
    items: list[ActionQueueItemResponse] = Field(default_factory=list)


class RecommendedActionStatusListResponse(BaseModel):
    statuses: list[RecommendedActionStatus]
    events: list[RecommendedActionStatusEvent] = Field(default_factory=list)
    verifications: list[RecommendedActionVerification] = Field(default_factory=list)
    verification_results: list[RecommendedActionVerificationResult] = Field(default_factory=list)


class SpreadsheetSyncRequest(BaseModel):
    spreadsheet_url: str = ""
    spreadsheet_id: str
    sheet_id: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class SpreadsheetRerunRequest(BaseModel):
    spreadsheet_url: str = ""
    spreadsheet_id: str
    sheet_id: str
    row_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    artifact_group_id: str = ""
    queue_priority: str = ""
    baseline_trials: int = Field(default=5, ge=0, le=5)
    auto_run: bool = True
    auto_closure: bool = False
    submit_controlled_probes: bool = False
    writeback: bool = False


class SpreadsheetRerunAutoClosureReport(BaseModel):
    job_id: str
    case_id: str
    closure: AutoDebugClosureResult
    report_artifact_url: str
    writeback_status: str


class SpreadsheetRerunApiResult(BaseModel):
    imported_case_ids: list[str]
    imported_rows: list[SpreadsheetImportedRowResponse]
    rejected_rows: list[SpreadsheetRejectedRow]
    skipped_row_ids: list[str]
    jobs: list[SubmittedDebugJob]
    batch: DebugBatchProgressResponse | None = None
    auto_closure_reports: list[SpreadsheetRerunAutoClosureReport] = Field(default_factory=list)


class LarkSpreadsheetStatusResponse(BaseModel):
    configured: bool
    spreadsheet_id: str
    sheet_id: str
    lark_cli_timeout_seconds: int
    connector_mode: str = "cli"
    connector_identity: str = "unknown"
    connector_profile: str = ""
    connector_auth_status: str = "unknown"
    connector_token_status: str = "unknown"
    connectivity_status: Literal["not_checked", "ok", "failed"] = "not_checked"
    error_message: str = ""
    error_type: str = ""
    permission_scopes: list[str] = Field(default_factory=list)
    console_url: str = ""
    risk_action: str = ""


class SpreadsheetWritebackAuditSummaryResponse(BaseModel):
    by_status: dict[str, int]
    total_count: int


class SpreadsheetWritebackAuditListResponse(BaseModel):
    audits: list[SpreadsheetWritebackAudit]
    total_count: int


class LarkOperationAuditListResponse(BaseModel):
    audits: list[LarkOperationAudit]
    total_count: int


class LarkScopeRequirementStatus(BaseModel):
    service: str
    operation: str
    required_scopes: list[str]
    risk_level: Literal["read", "write"]
    identity: str
    confirmation_required: bool
    repair_hint: str
    console_url: str
    status: Literal["unknown", "not_observed_missing", "missing_recently"]
    recent_missing_scopes: list[str] = Field(default_factory=list)
    recent_failure_count: int = 0


class LarkScopeCheckResponse(BaseModel):
    connector_mode: str
    connector_identity: str
    connector_profile: str
    auth_check_status: Literal["not_verified"] = "not_verified"
    requirements: list[LarkScopeRequirementStatus]
    recent_missing_scopes: list[str] = Field(default_factory=list)
    repair_steps: list[str] = Field(default_factory=list)
    console_url: str = LARK_PERMISSION_CONSOLE_URL


class WorkerRuntimeStatus(AsyncJobWorkerStatus):
    report_base_url: str
    auto_writeback_enabled: bool


class ObservabilityJobSummary(BaseModel):
    by_status: dict[str, int]
    total_count: int
    pending_count: int
    running_count: int
    failed_count: int
    completed_count: int


class ObservabilityEvidenceSummary(BaseModel):
    total_evidence: int
    failed_judgements: int
    response_parse_errors: int
    model_call_errors: int
    average_latency_ms: float


class ObservabilityHealthSummary(BaseModel):
    level: Literal["healthy", "degraded", "critical"]
    reasons: list[str]
    actions: list[str]


class ObservabilityUsageSummary(BaseModel):
    model_call_count: int
    prompt_character_count: int
    estimated_cost_units: float
    budget_units: float
    budget_status: Literal["not_configured", "within_budget", "over_budget"]
    budget_utilization: float
    budget_enforcement_enabled: bool


class ObservabilityStrategyFeedbackSummary(BaseModel):
    total_follow_ups: int
    pending_count: int
    passed_stop_condition_count: int
    needs_escalation_count: int


class ObservabilityTargetedProbeFeedbackSummary(BaseModel):
    total_probes: int
    pending_count: int
    target_cleared_count: int
    target_still_failing_count: int
    inconclusive_count: int
    max_depth_reached_count: int


class ObservabilityHumanHandoffFeedbackSummary(BaseModel):
    total_handoffs: int
    pending_count: int
    acknowledged_count: int
    in_progress_count: int
    resolved_count: int
    wont_fix_count: int
    open_count: int


class ObservabilityFinalAttributionVerificationFeedbackSummary(BaseModel):
    total_verifications: int
    pending_count: int
    resolved_count: int
    not_resolved_count: int
    inconclusive_count: int


class ObservabilityFinalAttributionRecoveryFeedbackSummary(BaseModel):
    total_recoveries: int
    pending_count: int
    closed_count: int
    reopen_count: int
    inconclusive_count: int


class ObservabilitySummaryResponse(BaseModel):
    jobs: ObservabilityJobSummary
    worker: WorkerRuntimeStatus
    writeback_audits: SpreadsheetWritebackAuditSummaryResponse
    evidence: ObservabilityEvidenceSummary
    strategy_feedback: ObservabilityStrategyFeedbackSummary
    targeted_probe_feedback: ObservabilityTargetedProbeFeedbackSummary
    human_handoff_feedback: ObservabilityHumanHandoffFeedbackSummary
    final_attribution_verification_feedback: (
        ObservabilityFinalAttributionVerificationFeedbackSummary
    )
    final_attribution_recovery_feedback: ObservabilityFinalAttributionRecoveryFeedbackSummary
    health: ObservabilityHealthSummary
    usage: ObservabilityUsageSummary
    performance: dict[str, object] = Field(default_factory=dict)


class PerformanceAggregateResponse(BaseModel):
    component: str
    operation: str
    count: int
    failed_count: int
    avg_ms: float
    p50_ms: int
    p95_ms: int
    max_ms: int
    latest_ms: int


class PerformanceEventResponse(BaseModel):
    component: str
    operation: str
    duration_ms: int
    status: str
    metadata: dict[str, object]
    occurred_at: str


class PerformanceSummaryResponse(BaseModel):
    total_count: int
    aggregates: list[PerformanceAggregateResponse]
    recent_events: list[PerformanceEventResponse]


class DebugCaseSummary(BaseModel):
    case_id: str
    image_uri: str
    avg_score: float
    debug_status: str
    root_cause: str
    box_region_count: int


class DebugCaseListResponse(BaseModel):
    cases: list[DebugCaseSummary]
    total_count: int
    filtered_count: int

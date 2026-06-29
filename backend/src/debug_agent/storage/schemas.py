from __future__ import annotations

from pydantic import BaseModel, Field

class SpreadsheetRowMapping(BaseModel):
    spreadsheet_id: str
    sheet_id: str
    row_id: str
    case_id: str
    job_id: str
    created_at: str
    updated_at: str


class SpreadsheetWritebackAudit(BaseModel):
    job_id: str
    status: str
    row_id: str
    report_url: str
    fields: dict[str, str]
    error_message: str
    created_at: str
    updated_at: str


class LarkReportDocument(BaseModel):
    job_id: str
    status: str
    document_url: str
    document_token: str
    internal_report_url: str
    error_message: str
    created_at: str
    updated_at: str


class LarkOperationAudit(BaseModel):
    audit_id: int
    actor: str
    connector_mode: str
    identity: str
    profile: str
    service: str
    operation: str
    status: str
    context: str
    error_type: str
    hint: str
    permission_scopes: list[str]
    console_url: str
    risk_action: str
    duration_ms: int
    created_at: str


class LarkWriteConfirmation(BaseModel):
    confirmation_id: str
    actor: str
    service: str
    operation: str
    resource_id: str
    resource_summary: str
    risk_action: str
    required_scopes: list[str]
    status: str
    note: str
    created_at: str
    expires_at: str
    confirmed_at: str
    confirmed_by: str


class LarkAuthSession(BaseModel):
    auth_session_id: str
    actor: str
    identity: str
    profile: str
    scopes: list[str]
    state: str
    auth_url: str
    redirect_url: str
    status: str
    note: str
    created_at: str
    expires_at: str
    completed_at: str
    completed_by: str


class LarkBotPendingCommand(BaseModel):
    command_id: str
    actor: str
    open_id: str
    chat_id: str
    message_id: str
    tenant_key: str
    identity: str
    profile: str
    command_text: str
    action_kind: str
    action: dict[str, object]
    card: dict[str, object]
    status: str
    note: str
    execution_result: dict[str, object]
    error_message: str
    created_at: str
    expires_at: str
    confirmed_at: str
    confirmed_by: str
    executed_at: str


class XiaoDExecutionRun(BaseModel):
    run_id: str
    tenant_key: str
    chat_id: str
    open_id: str
    command_id: str
    batch_id: str
    job_id: str
    action_kind: str
    status: str
    summary: dict[str, object]
    created_at: str
    updated_at: str
    completed_at: str


class XiaoDPendingDecision(BaseModel):
    decision_id: str
    tenant_key: str
    chat_id: str
    open_id: str
    decision_kind: str
    command_id: str
    run_id: str
    status: str
    payload: dict[str, object]
    note: str
    created_at: str
    expires_at: str
    resolved_at: str
    resolved_by: str


class XiaoDCommandAudit(BaseModel):
    audit_id: int
    tenant_key: str
    chat_id: str
    open_id: str
    command_id: str
    run_id: str
    decision_id: str
    event_kind: str
    status: str
    actor: str
    reason: str
    payload: dict[str, object]
    created_at: str


class LarkBotSetupAcknowledgement(BaseModel):
    acknowledgement_id: int
    item_key: str
    actor: str
    evidence: str
    note: str
    created_at: str


class LarkBotBadcaseDraft(BaseModel):
    draft_id: str
    actor: str
    open_id: str
    chat_id: str
    message_id: str
    status: str
    source_text: str
    input_source: str
    model_output: str
    expected_output: str
    issue_summary: str
    task_type: str
    scoring_standard: str
    attachments: list[dict[str, object]]
    links: list[str]
    missing_fields: list[str]
    progress_notified_keys: list[str] = Field(default_factory=list)
    progress_panel_message_id: str = ""
    submitted_case_id: str
    submitted_job_id: str
    error_message: str
    created_at: str
    updated_at: str


class LarkNotificationOutbox(BaseModel):
    notification_id: str
    kind: str
    dedupe_key: str
    status: str
    draft_id: str
    job_id: str
    case_id: str
    job_status: str
    progress_key: str
    payload: dict[str, object]
    envelope: dict[str, object]
    attempts: int
    last_error: str
    created_at: str
    updated_at: str
    sent_at: str


class RecommendedActionStatus(BaseModel):
    job_id: str
    action_index: int
    status: str
    actor: str
    note: str
    created_at: str
    updated_at: str


class RecommendedActionStatusEvent(BaseModel):
    event_id: int
    job_id: str
    action_index: int
    status: str
    actor: str
    note: str
    created_at: str


class RecommendedActionVerification(BaseModel):
    job_id: str
    action_index: int
    verification_job_id: str
    actor: str
    note: str
    created_at: str


class StrategyFollowUpJob(BaseModel):
    source_job_id: str
    stage: str
    planned_steps: str
    follow_up_job_id: str
    actor: str
    note: str
    created_at: str


class TargetedProbeJob(BaseModel):
    source_job_id: str
    source: str
    target_id: str
    planned_steps: str
    probe_job_id: str
    parent_probe_job_id: str
    trigger_outcome: str
    actor: str
    note: str
    created_at: str


class HumanHandoffStatus(BaseModel):
    job_id: str
    target_id: str
    status: str
    actor: str
    note: str
    created_at: str
    updated_at: str


class DebugRunStage(BaseModel):
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


class DebugBatch(BaseModel):
    batch_id: str
    status: str
    total_jobs: int
    max_concurrency: int
    retry_policy: dict[str, object]
    created_at: str
    updated_at: str
    started_at: str
    completed_at: str


class DebugJobAttempt(BaseModel):
    job_id: str
    attempt_index: int
    batch_id: str
    status: str
    failure_type: str
    failure_stage: str
    error_message: str
    retry_decision: str
    started_at: str
    finished_at: str
    duration_ms: int

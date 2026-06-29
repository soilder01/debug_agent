from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DebugJobRow(Base):
    __tablename__ = "debug_jobs"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    artifact_group_id: Mapped[str] = mapped_column(
        String(120), default="single", server_default="single", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    baseline_trials: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class DebugRunStageRow(Base):
    __tablename__ = "debug_run_stages"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    stage: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    input_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    failure_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class DebugBatchRow(Base):
    __tablename__ = "debug_batches"

    batch_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(40), default="created", server_default="created", index=True
    )
    total_jobs: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    retry_policy_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    started_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    completed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class DebugJobAttemptRow(Base):
    __tablename__ = "debug_job_attempts"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    attempt_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(
        String(120), default="single", server_default="single", index=True
    )
    status: Mapped[str] = mapped_column(
        String(40), default="running", server_default="running", index=True
    )
    failure_type: Mapped[str] = mapped_column(
        String(120), default="", server_default="", index=True
    )
    failure_stage: Mapped[str] = mapped_column(
        String(80), default="", server_default="", index=True
    )
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    retry_decision: Mapped[str] = mapped_column(
        String(120), default="", server_default="", index=True
    )
    started_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    finished_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class DebugCaseRow(Base):
    __tablename__ = "debug_cases"

    case_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_json: Mapped[str] = mapped_column(Text)
    box_region_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", index=True
    )


class SpreadsheetRowMappingRow(Base):
    __tablename__ = "spreadsheet_row_mappings"

    spreadsheet_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    sheet_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    row_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    job_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class SpreadsheetWritebackAuditRow(Base):
    __tablename__ = "spreadsheet_writeback_audits"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    row_id: Mapped[str] = mapped_column(String(160), default="", server_default="")
    report_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    fields_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class LarkReportDocumentRow(Base):
    __tablename__ = "lark_report_documents"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    document_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    document_token: Mapped[str] = mapped_column(String(240), default="", server_default="")
    internal_report_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class LarkOperationAuditRow(Base):
    __tablename__ = "lark_operation_audits"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    connector_mode: Mapped[str] = mapped_column(
        String(40), default="cli", server_default="cli", index=True
    )
    identity: Mapped[str] = mapped_column(
        String(40), default="unknown", server_default="unknown", index=True
    )
    profile: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    service: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    operation: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    context: Mapped[str] = mapped_column(Text, default="", server_default="")
    error_type: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    hint: Mapped[str] = mapped_column(Text, default="", server_default="")
    permission_scopes_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    console_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    risk_action: Mapped[str] = mapped_column(String(160), default="", server_default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class LarkWriteConfirmationRow(Base):
    __tablename__ = "lark_write_confirmations"

    confirmation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    service: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    operation: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    resource_id: Mapped[str] = mapped_column(String(240), default="", server_default="", index=True)
    resource_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    risk_action: Mapped[str] = mapped_column(String(160), default="", server_default="")
    required_scopes_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    confirmed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    confirmed_by: Mapped[str] = mapped_column(String(120), default="", server_default="")


class LarkAuthSessionRow(Base):
    __tablename__ = "lark_auth_sessions"

    auth_session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    identity: Mapped[str] = mapped_column(
        String(40), default="user", server_default="user", index=True
    )
    profile: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    state: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    auth_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    redirect_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    completed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    completed_by: Mapped[str] = mapped_column(String(120), default="", server_default="")


class LarkBotPendingCommandRow(Base):
    __tablename__ = "lark_bot_pending_commands"

    command_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    open_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    chat_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    message_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    tenant_key: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    identity: Mapped[str] = mapped_column(
        String(40), default="bot", server_default="bot", index=True
    )
    profile: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    command_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    action_kind: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    action_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    card_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    execution_result_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    confirmed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    confirmed_by: Mapped[str] = mapped_column(String(120), default="", server_default="")
    executed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class XiaoDExecutionRunRow(Base):
    __tablename__ = "xiaod_execution_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_key: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    chat_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    open_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    command_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    batch_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    job_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    action_kind: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(
        String(40), default="active", server_default="active", index=True
    )
    summary_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    completed_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class XiaoDPendingDecisionRow(Base):
    __tablename__ = "xiaod_pending_decisions"

    decision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_key: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    chat_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    open_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    decision_kind: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    command_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    run_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    resolved_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    resolved_by: Mapped[str] = mapped_column(String(120), default="", server_default="")


class XiaoDCommandAuditRow(Base):
    __tablename__ = "xiaod_command_audits"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_key: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    chat_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    open_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    command_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    run_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    decision_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    event_kind: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class LarkBotSetupAcknowledgementRow(Base):
    __tablename__ = "lark_bot_setup_acknowledgements"

    acknowledgement_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_key: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    evidence: Mapped[str] = mapped_column(Text, default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class LarkBotBadcaseDraftRow(Base):
    __tablename__ = "lark_bot_badcase_drafts"

    draft_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    open_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    chat_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    message_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(
        String(40), default="collecting", server_default="collecting", index=True
    )
    source_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    input_source: Mapped[str] = mapped_column(Text, default="", server_default="")
    model_output: Mapped[str] = mapped_column(Text, default="", server_default="")
    expected_output: Mapped[str] = mapped_column(Text, default="", server_default="")
    issue_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    task_type: Mapped[str] = mapped_column(
        String(80), default="generic_json", server_default="generic_json", index=True
    )
    scoring_standard: Mapped[str] = mapped_column(Text, default="", server_default="")
    attachments_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    links_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    missing_fields_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    progress_notified_keys_json: Mapped[str] = mapped_column(
        Text, default="[]", server_default="[]"
    )
    progress_panel_message_id: Mapped[str] = mapped_column(
        String(120), default="", server_default="", index=True
    )
    submitted_case_id: Mapped[str] = mapped_column(
        String(120), default="", server_default="", index=True
    )
    submitted_job_id: Mapped[str] = mapped_column(
        String(80), default="", server_default="", index=True
    )
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class LarkNotificationOutboxRow(Base):
    __tablename__ = "lark_notification_outbox"

    notification_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    kind: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(300), default="", server_default="", index=True)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    draft_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    job_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    case_id: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    job_status: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    progress_key: Mapped[str] = mapped_column(
        String(300), default="", server_default="", index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    envelope_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")
    sent_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class RecommendedActionStatusRow(Base):
    __tablename__ = "recommended_action_statuses"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    action_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class RecommendedActionStatusEventRow(Base):
    __tablename__ = "recommended_action_status_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(80), index=True)
    action_index: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class RecommendedActionVerificationRow(Base):
    __tablename__ = "recommended_action_verifications"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    action_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    verification_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class StrategyFollowUpJobRow(Base):
    __tablename__ = "strategy_follow_up_jobs"

    source_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    stage: Mapped[str] = mapped_column(String(120), primary_key=True)
    follow_up_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    planned_steps: Mapped[str] = mapped_column(Text, default="", server_default="")
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class TargetedProbeJobRow(Base):
    __tablename__ = "targeted_probe_jobs"

    source_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source: Mapped[str] = mapped_column(
        String(80), default="targeted_probe", server_default="targeted_probe"
    )
    target_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    probe_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    parent_probe_job_id: Mapped[str] = mapped_column(String(80), default="", server_default="")
    trigger_outcome: Mapped[str] = mapped_column(String(80), default="", server_default="")
    planned_steps: Mapped[str] = mapped_column(Text, default="", server_default="")
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class HumanHandoffStatusRow(Base):
    __tablename__ = "human_handoff_statuses"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", server_default="pending", index=True
    )
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class EvidenceRow(Base):
    __tablename__ = "evidence"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    trial: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    model_provider: Mapped[str] = mapped_column(String(80), default="", server_default="")
    model_id: Mapped[str] = mapped_column(String(160), default="", server_default="")
    request_summary_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    input_excerpt: Mapped[str] = mapped_column(Text, default="", server_default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    response_parse_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    model_call_error_type: Mapped[str] = mapped_column(String(120), default="", server_default="")
    model_call_error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    image_artifacts_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    artifacts_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str] = mapped_column(Text)
    raw_output: Mapped[str] = mapped_column(Text)

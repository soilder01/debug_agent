from __future__ import annotations

import json
from datetime import UTC, datetime

from debug_agent.judging.runner import JudgeResult
from debug_agent.storage.models import (
    DebugBatchRow,
    DebugJobAttemptRow,
    DebugRunStageRow,
    HumanHandoffStatusRow,
    LarkAuthSessionRow,
    LarkBotBadcaseDraftRow,
    LarkBotPendingCommandRow,
    LarkBotSetupAcknowledgementRow,
    LarkNotificationOutboxRow,
    LarkOperationAuditRow,
    LarkReportDocumentRow,
    LarkWriteConfirmationRow,
    RecommendedActionStatusEventRow,
    RecommendedActionStatusRow,
    RecommendedActionVerificationRow,
    SpreadsheetWritebackAuditRow,
    StrategyFollowUpJobRow,
    TargetedProbeJobRow,
    XiaoDCommandAuditRow,
    XiaoDExecutionRunRow,
    XiaoDPendingDecisionRow,
)
from debug_agent.storage.schemas import (
    DebugBatch,
    DebugJobAttempt,
    DebugRunStage,
    HumanHandoffStatus,
    LarkAuthSession,
    LarkBotBadcaseDraft,
    LarkBotPendingCommand,
    LarkBotSetupAcknowledgement,
    LarkNotificationOutbox,
    LarkOperationAudit,
    LarkReportDocument,
    LarkWriteConfirmation,
    RecommendedActionStatus,
    RecommendedActionStatusEvent,
    RecommendedActionVerification,
    SpreadsheetWritebackAudit,
    StrategyFollowUpJob,
    TargetedProbeJob,
    XiaoDCommandAudit,
    XiaoDExecutionRun,
    XiaoDPendingDecision,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _duration_percentile(sorted_durations: list[int], percentile: float) -> int:
    if not sorted_durations:
        return 0
    index = min(
        len(sorted_durations) - 1, max(0, int(round((len(sorted_durations) - 1) * percentile)))
    )
    return sorted_durations[index]


def _debug_run_stage_from_row(row: DebugRunStageRow) -> DebugRunStage:
    input_payload = json.loads(row.input_json)
    output_payload = json.loads(row.output_json)
    if not isinstance(input_payload, dict):
        raise ValueError(f"Debug run stage input must be an object: {row.job_id}/{row.stage}")
    if not isinstance(output_payload, dict):
        raise ValueError(f"Debug run stage output must be an object: {row.job_id}/{row.stage}")
    return DebugRunStage(
        job_id=row.job_id,
        stage=row.stage,
        status=row.status,
        input=input_payload,
        output=output_payload,
        failure_reason=row.failure_reason,
        retryable=row.retryable,
        attempt_count=row.attempt_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _debug_batch_from_row(row: DebugBatchRow) -> DebugBatch:
    retry_policy = json.loads(row.retry_policy_json)
    if not isinstance(retry_policy, dict):
        retry_policy = {}
    return DebugBatch(
        batch_id=row.batch_id,
        status=row.status,
        total_jobs=row.total_jobs,
        max_concurrency=row.max_concurrency,
        retry_policy=retry_policy,
        created_at=row.created_at,
        updated_at=row.updated_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def _debug_job_attempt_from_row(row: DebugJobAttemptRow) -> DebugJobAttempt:
    return DebugJobAttempt(
        job_id=row.job_id,
        attempt_index=row.attempt_index,
        batch_id=row.batch_id,
        status=row.status,
        failure_type=row.failure_type,
        failure_stage=row.failure_stage,
        error_message=row.error_message,
        retry_decision=row.retry_decision,
        started_at=row.started_at,
        finished_at=row.finished_at,
        duration_ms=row.duration_ms,
    )


def _duration_ms(started_at: str, finished_at: str) -> int:
    try:
        started = datetime.fromisoformat(started_at)
        finished = datetime.fromisoformat(finished_at)
    except ValueError:
        return 0
    return max(0, int((finished - started).total_seconds() * 1000))


def _debug_run_stage_sort_key(stage: str) -> tuple[int, str]:
    stage_order = {
        "baseline": 0,
        "hypothesis": 1,
        "intervention": 2,
        "causal_comparison": 3,
        "targeted": 4,
        "verification": 5,
        "attribution": 6,
        "writeback": 7,
        "auto_closure": 8,
    }
    return (stage_order.get(stage, 100), stage)


def _judge_result_from_payload(*, score: int, evidence_id: str, payload: object) -> JudgeResult:
    if isinstance(payload, list):
        return JudgeResult(score=score, reasons=[str(reason) for reason in payload])
    if not isinstance(payload, dict):
        raise ValueError(f"Evidence judge payload must be an object or reasons list: {evidence_id}")
    payload_with_score = dict(payload)
    payload_with_score["score"] = score
    return JudgeResult.model_validate(payload_with_score)


def _spreadsheet_writeback_audit_from_row(
    row: SpreadsheetWritebackAuditRow,
) -> SpreadsheetWritebackAudit:
    fields = json.loads(row.fields_json)
    if not isinstance(fields, dict):
        raise ValueError(f"Spreadsheet writeback fields must be an object: {row.job_id}")
    return SpreadsheetWritebackAudit(
        job_id=row.job_id,
        status=row.status,
        row_id=row.row_id,
        report_url=row.report_url,
        fields={str(key): str(value) for key, value in fields.items()},
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lark_report_document_from_row(row: LarkReportDocumentRow) -> LarkReportDocument:
    return LarkReportDocument(
        job_id=row.job_id,
        status=row.status,
        document_url=row.document_url,
        document_token=row.document_token,
        internal_report_url=row.internal_report_url,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lark_notification_outbox_from_row(
    row: LarkNotificationOutboxRow,
) -> LarkNotificationOutbox:
    return LarkNotificationOutbox(
        notification_id=row.notification_id,
        kind=row.kind,
        dedupe_key=row.dedupe_key,
        status=row.status,
        draft_id=row.draft_id,
        job_id=row.job_id,
        case_id=row.case_id,
        job_status=row.job_status,
        progress_key=row.progress_key,
        payload=_json_object(row.payload_json),
        envelope=_json_object(row.envelope_json),
        attempts=row.attempts,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sent_at=row.sent_at,
    )


def _outbox_envelope_json_with_state(envelope_json: str, state: str) -> str:
    envelope = _json_object(envelope_json)
    envelope["delivery_state"] = state
    return json.dumps(envelope)


def _json_object(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _lark_operation_audit_from_row(row: LarkOperationAuditRow) -> LarkOperationAudit:
    permission_scopes = json.loads(row.permission_scopes_json)
    if not isinstance(permission_scopes, list):
        raise ValueError(f"Lark operation permission scopes must be a list: {row.audit_id}")
    return LarkOperationAudit(
        audit_id=row.audit_id,
        actor=row.actor,
        connector_mode=row.connector_mode,
        identity=row.identity,
        profile=row.profile,
        service=row.service,
        operation=row.operation,
        status=row.status,
        context=row.context,
        error_type=row.error_type,
        hint=row.hint,
        permission_scopes=[str(item) for item in permission_scopes],
        console_url=row.console_url,
        risk_action=row.risk_action,
        duration_ms=row.duration_ms,
        created_at=row.created_at,
    )


def _lark_write_confirmation_from_row(row: LarkWriteConfirmationRow) -> LarkWriteConfirmation:
    required_scopes = json.loads(row.required_scopes_json)
    if not isinstance(required_scopes, list):
        raise ValueError(f"Lark write confirmation scopes must be a list: {row.confirmation_id}")
    return LarkWriteConfirmation(
        confirmation_id=row.confirmation_id,
        actor=row.actor,
        service=row.service,
        operation=row.operation,
        resource_id=row.resource_id,
        resource_summary=row.resource_summary,
        risk_action=row.risk_action,
        required_scopes=[str(item) for item in required_scopes],
        status=row.status,
        note=row.note,
        created_at=row.created_at,
        expires_at=row.expires_at,
        confirmed_at=row.confirmed_at,
        confirmed_by=row.confirmed_by,
    )


def _lark_auth_session_from_row(row: LarkAuthSessionRow) -> LarkAuthSession:
    scopes = json.loads(row.scopes_json)
    if not isinstance(scopes, list):
        raise ValueError(f"Lark auth session scopes must be a list: {row.auth_session_id}")
    return LarkAuthSession(
        auth_session_id=row.auth_session_id,
        actor=row.actor,
        identity=row.identity,
        profile=row.profile,
        scopes=[str(item) for item in scopes],
        state=row.state,
        auth_url=row.auth_url,
        redirect_url=row.redirect_url,
        status=row.status,
        note=row.note,
        created_at=row.created_at,
        expires_at=row.expires_at,
        completed_at=row.completed_at,
        completed_by=row.completed_by,
    )


def _lark_bot_pending_command_from_row(row: LarkBotPendingCommandRow) -> LarkBotPendingCommand:
    action = json.loads(row.action_json)
    card = json.loads(row.card_json)
    execution_result = json.loads(row.execution_result_json)
    if not isinstance(action, dict):
        raise ValueError(f"Lark bot pending command action must be an object: {row.command_id}")
    if not isinstance(card, dict):
        raise ValueError(f"Lark bot pending command card must be an object: {row.command_id}")
    if not isinstance(execution_result, dict):
        execution_result = {}
    return LarkBotPendingCommand(
        command_id=row.command_id,
        actor=row.actor,
        open_id=row.open_id,
        chat_id=row.chat_id,
        message_id=row.message_id,
        tenant_key=row.tenant_key,
        identity=row.identity,
        profile=row.profile,
        command_text=row.command_text,
        action_kind=row.action_kind,
        action=action,
        card=card,
        status=row.status,
        note=row.note,
        execution_result=execution_result,
        error_message=row.error_message,
        created_at=row.created_at,
        expires_at=row.expires_at,
        confirmed_at=row.confirmed_at,
        confirmed_by=row.confirmed_by,
        executed_at=row.executed_at,
    )


def _xiaod_execution_run_from_row(row: XiaoDExecutionRunRow) -> XiaoDExecutionRun:
    return XiaoDExecutionRun(
        run_id=row.run_id,
        tenant_key=row.tenant_key,
        chat_id=row.chat_id,
        open_id=row.open_id,
        command_id=row.command_id,
        batch_id=row.batch_id,
        job_id=row.job_id,
        action_kind=row.action_kind,
        status=row.status,
        summary=_json_object(row.summary_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _xiaod_pending_decision_from_row(row: XiaoDPendingDecisionRow) -> XiaoDPendingDecision:
    return XiaoDPendingDecision(
        decision_id=row.decision_id,
        tenant_key=row.tenant_key,
        chat_id=row.chat_id,
        open_id=row.open_id,
        decision_kind=row.decision_kind,
        command_id=row.command_id,
        run_id=row.run_id,
        status=row.status,
        payload=_json_object(row.payload_json),
        note=row.note,
        created_at=row.created_at,
        expires_at=row.expires_at,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by,
    )


def _xiaod_command_audit_from_row(row: XiaoDCommandAuditRow) -> XiaoDCommandAudit:
    return XiaoDCommandAudit(
        audit_id=row.audit_id,
        tenant_key=row.tenant_key,
        chat_id=row.chat_id,
        open_id=row.open_id,
        command_id=row.command_id,
        run_id=row.run_id,
        decision_id=row.decision_id,
        event_kind=row.event_kind,
        status=row.status,
        actor=row.actor,
        reason=row.reason,
        payload=_json_object(row.payload_json),
        created_at=row.created_at,
    )


def _xiaod_command_audit_row_for_command(
    row: LarkBotPendingCommandRow,
    *,
    event_kind: str,
    status: str,
    actor: str,
    reason: str,
    created_at: str,
) -> XiaoDCommandAuditRow:
    return XiaoDCommandAuditRow(
        tenant_key=row.tenant_key,
        chat_id=row.chat_id,
        open_id=row.open_id,
        command_id=row.command_id,
        run_id="",
        decision_id="",
        event_kind=event_kind,
        status=status,
        actor=actor,
        reason=reason,
        payload_json=json.dumps({"action_kind": row.action_kind}),
        created_at=created_at,
    )


def _lark_bot_setup_acknowledgement_from_row(
    row: LarkBotSetupAcknowledgementRow,
) -> LarkBotSetupAcknowledgement:
    return LarkBotSetupAcknowledgement(
        acknowledgement_id=row.acknowledgement_id,
        item_key=row.item_key,
        actor=row.actor,
        evidence=row.evidence,
        note=row.note,
        created_at=row.created_at,
    )


def _lark_bot_badcase_draft_from_row(row: LarkBotBadcaseDraftRow) -> LarkBotBadcaseDraft:
    attachments = json.loads(row.attachments_json)
    links = json.loads(row.links_json)
    missing_fields = json.loads(row.missing_fields_json)
    progress_notified_keys = _json_string_list(row.progress_notified_keys_json)
    if not isinstance(attachments, list):
        attachments = []
    if not isinstance(links, list):
        links = []
    if not isinstance(missing_fields, list):
        missing_fields = []
    return LarkBotBadcaseDraft(
        draft_id=row.draft_id,
        actor=row.actor,
        open_id=row.open_id,
        chat_id=row.chat_id,
        message_id=row.message_id,
        status=row.status,
        source_text=row.source_text,
        input_source=row.input_source,
        model_output=row.model_output,
        expected_output=row.expected_output,
        issue_summary=row.issue_summary,
        task_type=row.task_type,
        scoring_standard=row.scoring_standard,
        attachments=[item for item in attachments if isinstance(item, dict)],
        links=[str(item) for item in links],
        missing_fields=[str(item) for item in missing_fields],
        progress_notified_keys=progress_notified_keys,
        progress_panel_message_id=row.progress_panel_message_id,
        submitted_case_id=row.submitted_case_id,
        submitted_job_id=row.submitted_job_id,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _json_string_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item)]


def _recommended_action_status_from_row(row: RecommendedActionStatusRow) -> RecommendedActionStatus:
    return RecommendedActionStatus(
        job_id=row.job_id,
        action_index=row.action_index,
        status=row.status,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recommended_action_status_event_from_row(
    row: RecommendedActionStatusEventRow,
) -> RecommendedActionStatusEvent:
    return RecommendedActionStatusEvent(
        event_id=row.event_id,
        job_id=row.job_id,
        action_index=row.action_index,
        status=row.status,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _recommended_action_verification_from_row(
    row: RecommendedActionVerificationRow,
) -> RecommendedActionVerification:
    return RecommendedActionVerification(
        job_id=row.job_id,
        action_index=row.action_index,
        verification_job_id=row.verification_job_id,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _strategy_follow_up_job_from_row(row: StrategyFollowUpJobRow) -> StrategyFollowUpJob:
    return StrategyFollowUpJob(
        source_job_id=row.source_job_id,
        stage=row.stage,
        planned_steps=row.planned_steps,
        follow_up_job_id=row.follow_up_job_id,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _targeted_probe_job_from_row(row: TargetedProbeJobRow) -> TargetedProbeJob:
    return TargetedProbeJob(
        source_job_id=row.source_job_id,
        source=row.source,
        target_id=row.target_id,
        planned_steps=row.planned_steps,
        probe_job_id=row.probe_job_id,
        parent_probe_job_id=row.parent_probe_job_id,
        trigger_outcome=row.trigger_outcome,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _human_handoff_status_from_row(row: HumanHandoffStatusRow) -> HumanHandoffStatus:
    return HumanHandoffStatus(
        job_id=row.job_id,
        target_id=row.target_id,
        status=row.status,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

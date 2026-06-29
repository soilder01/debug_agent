from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from debug_agent.lark.xiaod_command_parsing import (
    BOT_MENTION_PREFIXES as BOT_MENTION_PREFIXES,
    COMMAND_PREFIXES as COMMAND_PREFIXES,
    HELP_KEYWORDS as HELP_KEYWORDS,
    LARK_RESOURCE_MARKERS as LARK_RESOURCE_MARKERS,
    SPREADSHEET_RERUN_WRITEBACK_OPTION_MARKERS as SPREADSHEET_RERUN_WRITEBACK_OPTION_MARKERS,
    SPREADSHEET_URL_PATTERN as SPREADSHEET_URL_PATTERN,
    WRITEBACK_DECISION_SKIP_MARKERS as WRITEBACK_DECISION_SKIP_MARKERS,
    assistant_question_and_model as assistant_question_and_model,
    command_text_for_backend as command_text_for_backend,
    first_spreadsheet_url as first_spreadsheet_url,
    has_command_prefix as has_command_prefix,
    has_lark_resource_link as has_lark_resource_link,
    human_handoff_status_command as human_handoff_status_command,
    is_ambiguous_continue_request as is_ambiguous_continue_request,
    is_badcase_draft_followup_request as is_badcase_draft_followup_request,
    is_badcase_intake_guidance_request as is_badcase_intake_guidance_request,
    is_badcase_intake_message as is_badcase_intake_message,
    is_cancel_current_job_request as is_cancel_current_job_request,
    is_cancel_draft_request as is_cancel_draft_request,
    is_confirm_draft_request as is_confirm_draft_request,
    is_contextual_cancel_request as is_contextual_cancel_request,
    is_contextual_pause_request as is_contextual_pause_request,
    is_contextual_report_request as is_contextual_report_request,
    is_contextual_resume_request as is_contextual_resume_request,
    is_contextual_writeback_request as is_contextual_writeback_request,
    is_current_progress_request as is_current_progress_request,
    is_help_request as is_help_request,
    is_pause_current_job_request as is_pause_current_job_request,
    is_pending_command_continue_request as is_pending_command_continue_request,
    is_pending_command_decline_request as is_pending_command_decline_request,
    is_pending_command_delete_request as is_pending_command_delete_request,
    is_pending_command_retain_request as is_pending_command_retain_request,
    is_recent_tasks_request as is_recent_tasks_request,
    is_result_confidence_request as is_result_confidence_request,
    is_resume_current_job_request as is_resume_current_job_request,
    is_writeback_decision_skip_request as is_writeback_decision_skip_request,
    is_writeback_decision_sync_request as is_writeback_decision_sync_request,
    natural_command_text as natural_command_text,
    natural_spreadsheet_operation_command as natural_spreadsheet_operation_command,
    natural_spreadsheet_row_batch_command as natural_spreadsheet_row_batch_command,
    needs_context_to_resolve_reference as needs_context_to_resolve_reference,
    normalized_text as normalized_text,
    recommended_action_status_command as recommended_action_status_command,
    sheet_id_from_spreadsheet_url as sheet_id_from_spreadsheet_url,
    spreadsheet_case_ids_from_natural_text as spreadsheet_case_ids_from_natural_text,
    spreadsheet_rerun_option_text as spreadsheet_rerun_option_text,
    spreadsheet_row_ids_from_natural_text as spreadsheet_row_ids_from_natural_text,
    strip_bot_mention_prefix as strip_bot_mention_prefix,
)


XiaoDTurnKind = Literal[
    "help",
    "confirm_badcase_draft",
    "cancel_badcase_draft",
    "badcase_draft_followup",
    "query_current_progress",
    "query_recent_tasks",
    "cancel_current_job",
    "pause_current_job",
    "resume_current_job",
    "continue_pending_command",
    "decline_pending_command",
    "retain_pending_command",
    "delete_pending_command",
    "sync_writeback_decision",
    "skip_writeback_decision",
    "backend_command",
    "save_badcase_draft",
    "badcase_intake_guidance",
    "clarify_intent",
    "assistant_chat",
]


@dataclass(frozen=True)
class XiaoDTurnRequest:
    text: str
    has_attachments: bool = False


@dataclass(frozen=True)
class XiaoDConversationContext:
    has_open_draft: bool = False
    has_ready_draft: bool = False
    latest_open_draft_status: str = ""
    latest_submitted_job_id: str = ""
    latest_submitted_job_status: str = ""
    latest_report_url: str = ""
    has_pending_command: bool = False
    has_pending_writeback_decision: bool = False


@dataclass(frozen=True)
class XiaoDTurnDecision:
    kind: XiaoDTurnKind
    clean_text: str
    backend_command: str = ""
    assistant_question: str = ""
    assistant_model_id: str = ""
    reason: str = ""
    extracted_fields: dict[str, str] = field(default_factory=dict)


def decide_xiaod_turn(
    request: XiaoDTurnRequest,
    *,
    context: XiaoDConversationContext | None = None,
) -> XiaoDTurnDecision:
    clean_text = strip_bot_mention_prefix(request.text)
    contextual_decision = contextual_turn_decision(
        clean_text,
        context=context,
    )
    if contextual_decision is not None:
        return contextual_decision
    if is_cancel_draft_request(clean_text):
        return XiaoDTurnDecision(
            kind="cancel_badcase_draft",
            clean_text=clean_text,
            reason="user_cancelled_latest_draft",
        )
    if is_confirm_draft_request(clean_text):
        return XiaoDTurnDecision(
            kind="confirm_badcase_draft",
            clean_text=clean_text,
            reason="user_confirmed_latest_draft",
        )
    if is_cancel_current_job_request(clean_text):
        return XiaoDTurnDecision(
            kind="cancel_current_job",
            clean_text=clean_text,
            reason="current_debug_job_cancel",
        )
    if is_pause_current_job_request(clean_text):
        return XiaoDTurnDecision(
            kind="pause_current_job",
            clean_text=clean_text,
            reason="current_debug_job_pause",
        )
    if is_resume_current_job_request(clean_text):
        return XiaoDTurnDecision(
            kind="resume_current_job",
            clean_text=clean_text,
            reason="current_debug_job_resume",
        )
    if is_help_request(clean_text):
        return XiaoDTurnDecision(kind="help", clean_text=clean_text, reason="help_request")
    if is_badcase_intake_guidance_request(clean_text):
        return XiaoDTurnDecision(
            kind="badcase_intake_guidance",
            clean_text=clean_text,
            reason="badcase_intake_guidance",
        )
    if is_current_progress_request(clean_text):
        return XiaoDTurnDecision(
            kind="query_current_progress",
            clean_text=clean_text,
            reason="current_debug_progress",
        )
    if is_recent_tasks_request(clean_text):
        return XiaoDTurnDecision(
            kind="query_recent_tasks",
            clean_text=clean_text,
            reason="recent_debug_tasks",
        )
    if is_badcase_draft_followup_request(clean_text):
        return XiaoDTurnDecision(
            kind="badcase_draft_followup",
            clean_text=clean_text,
            reason="latest_badcase_draft_status",
        )

    backend_command = command_text_for_backend(clean_text)
    if backend_command:
        return XiaoDTurnDecision(
            kind="backend_command",
            clean_text=clean_text,
            backend_command=backend_command,
            reason="mapped_to_debug_agent_api",
        )
    if is_badcase_intake_message(clean_text) or request.has_attachments:
        return XiaoDTurnDecision(
            kind="save_badcase_draft",
            clean_text=clean_text,
            reason="badcase_intake",
        )

    question, model_id = assistant_question_and_model(clean_text)
    return XiaoDTurnDecision(
        kind="assistant_chat",
        clean_text=clean_text,
        assistant_question=question,
        assistant_model_id=model_id,
        reason="project_assistant",
    )


def contextual_turn_decision(
    clean_text: str,
    *,
    context: XiaoDConversationContext | None,
) -> XiaoDTurnDecision | None:
    if context is None:
        return None
    normalized = normalized_text(clean_text).strip(" ?？。!！")
    compact = normalized.replace(" ", "")
    if not compact:
        return None
    if is_cancel_draft_request(clean_text):
        return XiaoDTurnDecision(
            kind="cancel_badcase_draft",
            clean_text=clean_text,
            reason="user_cancelled_latest_draft",
        )
    if is_confirm_draft_request(clean_text):
        return XiaoDTurnDecision(
            kind="confirm_badcase_draft",
            clean_text=clean_text,
            reason="user_confirmed_latest_draft",
        )
    if command_text_for_backend(clean_text):
        return None
    if context.has_pending_command:
        if is_pending_command_retain_request(compact):
            return XiaoDTurnDecision(
                kind="retain_pending_command",
                clean_text=clean_text,
                reason="contextual_retain_pending_command",
            )
        if is_pending_command_delete_request(compact):
            return XiaoDTurnDecision(
                kind="delete_pending_command",
                clean_text=clean_text,
                reason="contextual_delete_pending_command",
            )
        if is_pending_command_decline_request(compact):
            return XiaoDTurnDecision(
                kind="decline_pending_command",
                clean_text=clean_text,
                reason="contextual_decline_pending_command",
            )
        if is_pending_command_continue_request(compact):
            return XiaoDTurnDecision(
                kind="continue_pending_command",
                clean_text=clean_text,
                reason="contextual_continue_pending_command",
            )
    if context.has_pending_writeback_decision:
        if is_writeback_decision_skip_request(compact):
            return XiaoDTurnDecision(
                kind="skip_writeback_decision",
                clean_text=clean_text,
                reason="contextual_skip_writeback_decision",
            )
        if is_writeback_decision_sync_request(compact):
            return XiaoDTurnDecision(
                kind="sync_writeback_decision",
                clean_text=clean_text,
                reason="contextual_sync_writeback_decision",
            )
    if context.latest_submitted_job_id:
        if is_contextual_pause_request(compact):
            return XiaoDTurnDecision(
                kind="pause_current_job",
                clean_text=clean_text,
                reason="contextual_debug_job_pause",
            )
        if is_contextual_cancel_request(compact):
            return XiaoDTurnDecision(
                kind="cancel_current_job",
                clean_text=clean_text,
                reason="contextual_debug_job_cancel",
            )
        if is_contextual_resume_request(compact):
            return XiaoDTurnDecision(
                kind="resume_current_job",
                clean_text=clean_text,
                reason="contextual_debug_job_resume",
            )
    if natural_spreadsheet_row_batch_command(clean_text):
        return None
    if is_ambiguous_continue_request(compact):
        if context.has_ready_draft or context.has_open_draft:
            return XiaoDTurnDecision(
                kind="badcase_draft_followup",
                clean_text=clean_text,
                reason="contextual_continue_badcase_draft",
            )
        if context.latest_submitted_job_id:
            return XiaoDTurnDecision(
                kind="query_current_progress",
                clean_text=clean_text,
                reason="contextual_continue_current_job",
            )
        return XiaoDTurnDecision(
            kind="clarify_intent",
            clean_text=clean_text,
            reason="missing_context_for_continue",
        )
    if is_contextual_report_request(compact):
        if context.latest_submitted_job_id:
            if _job_has_terminal_report_context(context):
                return XiaoDTurnDecision(
                    kind="backend_command",
                    clean_text=clean_text,
                    backend_command=f"/debug report {context.latest_submitted_job_id}",
                    reason="contextual_latest_job_report",
                )
            return XiaoDTurnDecision(
                kind="query_current_progress",
                clean_text=clean_text,
                reason="contextual_report_not_ready",
            )
        if context.has_ready_draft or context.has_open_draft:
            return XiaoDTurnDecision(
                kind="query_current_progress",
                clean_text=clean_text,
                reason="contextual_report_draft_not_submitted",
            )
        return XiaoDTurnDecision(
            kind="clarify_intent",
            clean_text=clean_text,
            reason="missing_context_for_report",
        )
    if is_result_confidence_request(compact):
        if context.latest_submitted_job_id:
            if _job_has_terminal_report_context(context):
                return XiaoDTurnDecision(
                    kind="backend_command",
                    clean_text=clean_text,
                    backend_command=f"/debug report {context.latest_submitted_job_id}",
                    reason="contextual_result_explanation",
                )
            return XiaoDTurnDecision(
                kind="query_current_progress",
                clean_text=clean_text,
                reason="contextual_result_not_ready",
            )
        return XiaoDTurnDecision(
            kind="clarify_intent",
            clean_text=clean_text,
            reason="missing_context_for_result",
        )
    if is_contextual_writeback_request(compact):
        if context.latest_submitted_job_id:
            return XiaoDTurnDecision(
                kind="backend_command",
                clean_text=clean_text,
                backend_command=f"/debug report {context.latest_submitted_job_id}",
                reason="contextual_writeback_status",
            )
        return XiaoDTurnDecision(
            kind="clarify_intent",
            clean_text=clean_text,
            reason="missing_context_for_writeback",
        )
    if needs_context_to_resolve_reference(compact):
        if natural_spreadsheet_row_batch_command(clean_text):
            return None
        return XiaoDTurnDecision(
            kind="clarify_intent",
            clean_text=clean_text,
            reason="ambiguous_context_reference",
        )
    return None


def _job_has_terminal_report_context(context: XiaoDConversationContext) -> bool:
    if context.latest_report_url:
        return True
    return context.latest_submitted_job_status in {"completed", "failed", "cancelled"}

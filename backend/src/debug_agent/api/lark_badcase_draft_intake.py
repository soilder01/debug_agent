from __future__ import annotations

from collections.abc import Callable

from debug_agent.api.badcase_intake_parsers import (
    _append_source_text,
    _badcase_attachment_source,
    _badcase_fields_from_link_contexts,
    _badcase_input_source_from_links,
    _badcase_sheet_target_label,
    _debug_case_from_link_contexts,
    _dedupe_badcase_attachments,
    _extract_badcase_fields_from_text,
    _extract_links,
    _first_non_empty,
    _merge_string_lists,
    _missing_badcase_draft_fields,
    _missing_spreadsheet_fields_from_link_contexts,
    _normalized_badcase_task_type,
)
from debug_agent.api.lark_bot_routes import LarkBotBadcaseDraftRequest
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft


class LarkBadcaseDraftIntakeController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        link_contexts: Callable[[list[str], bool, str, str], list[dict[str, object]]],
        input_source_is_missing_placeholder: Callable[[str], bool],
        normalized_input_source: Callable[[str], str],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
    ) -> None:
        self._job_repository = job_repository
        self._link_contexts = link_contexts
        self._input_source_is_missing_placeholder = input_source_is_missing_placeholder
        self._normalized_input_source = normalized_input_source
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit

    def save_from_request(
        self,
        *,
        request: LarkBotBadcaseDraftRequest,
        actor: str,
        draft_id: str,
        existing: LarkBotBadcaseDraft | None = None,
    ) -> LarkBotBadcaseDraft:
        extracted = _extract_badcase_fields_from_text(request.text)
        links = _merge_string_lists(
            existing.links if existing else [], request.links, _extract_links(request.text)
        )
        link_contexts = self._link_contexts(
            links,
            request.resolve_link_content,
            actor,
            _badcase_sheet_target_label(request.text),
        )
        attachments = _dedupe_badcase_attachments(
            [
                *(existing.attachments if existing else []),
                *request.attachments,
                *link_contexts,
            ]
        )
        imported_debug_case = _debug_case_from_link_contexts(attachments)
        link_fields = _badcase_fields_from_link_contexts(attachments)
        input_source = _first_non_empty(
            request.input_source,
            extracted["input_source"],
            link_fields["input_source"],
            existing.input_source if existing else "",
            _badcase_input_source_from_links(link_contexts),
            _badcase_attachment_source(attachments),
        )
        if self._input_source_is_missing_placeholder(input_source):
            input_source = ""
        input_source = self._normalized_input_source(input_source)
        model_output = _first_non_empty(
            request.model_output,
            extracted["model_output"],
            link_fields["model_output"],
            existing.model_output if existing else "",
        )
        expected_output = _first_non_empty(
            request.expected_output,
            extracted["expected_output"],
            link_fields["expected_output"],
            existing.expected_output if existing else "",
        )
        issue_summary = _first_non_empty(
            request.issue_summary,
            extracted["issue_summary"],
            link_fields["issue_summary"],
            existing.issue_summary if existing else "",
        )
        task_type = _normalized_badcase_task_type(
            _first_non_empty(
                request.task_type,
                extracted["task_type"],
                link_fields["task_type"],
                existing.task_type if existing else "",
                "generic_json",
            )
        )
        scoring_standard = _first_non_empty(
            request.scoring_standard,
            extracted["scoring_standard"],
            link_fields["scoring_standard"],
            existing.scoring_standard if existing else "",
            "Compare model output against the expected output and explain mismatches.",
        )
        if imported_debug_case is not None:
            missing_fields = []
        else:
            missing_fields = _missing_spreadsheet_fields_from_link_contexts(link_contexts)
            if not missing_fields:
                missing_fields = _missing_badcase_draft_fields(
                    input_source=input_source,
                    model_output=model_output,
                    expected_output=expected_output,
                    issue_summary=issue_summary,
                )
        if existing is not None and existing.submitted_job_id:
            status = "submitted"
        else:
            status = "ready_for_confirmation" if not missing_fields else "needs_more_info"
        draft = self._job_repository().save_lark_bot_badcase_draft(
            draft_id=draft_id,
            actor=actor,
            open_id=request.open_id or (existing.open_id if existing else ""),
            chat_id=request.chat_id or (existing.chat_id if existing else ""),
            message_id=request.message_id or (existing.message_id if existing else ""),
            status=status,
            source_text=_append_source_text(existing.source_text if existing else "", request.text),
            input_source=input_source,
            model_output=model_output,
            expected_output=expected_output,
            issue_summary=issue_summary,
            task_type=task_type,
            scoring_standard=scoring_standard,
            attachments=attachments,
            links=links,
            missing_fields=missing_fields,
            submitted_case_id=existing.submitted_case_id if existing else "",
            submitted_job_id=existing.submitted_job_id if existing else "",
            error_message="",
        )
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="badcase_draft_saved",
            context=draft.draft_id,
            risk_action="badcase_intake",
        )
        return draft

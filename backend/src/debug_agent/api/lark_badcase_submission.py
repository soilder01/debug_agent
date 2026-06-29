from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import HTTPException

from debug_agent.api.badcase_intake_parsers import (
    _debug_case_from_link_contexts,
    _json_object_or_text,
    _object_string,
)
from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCancelRequest,
    LarkBotBadcaseDraftConfirmRequest,
    LarkBotBadcaseDraftConfirmResponse,
)
from debug_agent.artifacts.layout import safe_path_fragment
from debug_agent.cases.models import AnswerSet, DebugCase, HumanNotes, Prediction
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft


class LarkBadcaseSubmissionController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        job_service: Callable[[], DebugJobService],
        resolved_actor: Callable[[str], str],
        raise_if_usage_budget_blocks_submission: Callable[[], None],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._resolved_actor = resolved_actor
        self._raise_if_usage_budget_blocks_submission = raise_if_usage_budget_blocks_submission
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit

    def cancel(
        self,
        draft_id: str,
        request: LarkBotBadcaseDraftCancelRequest,
    ) -> LarkBotBadcaseDraft:
        repository = self._job_repository()
        draft = repository.get_lark_bot_badcase_draft(draft_id)
        if draft is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}"
            )
        if draft.status in {"submitted", "completed"}:
            raise HTTPException(
                status_code=409,
                detail=f"Badcase draft can no longer be cancelled: {draft.status}",
            )
        actor = self._resolved_actor(request.actor or draft.actor or draft.open_id)
        updated = repository.save_lark_bot_badcase_draft(
            draft_id=draft.draft_id,
            actor=actor,
            open_id=draft.open_id,
            chat_id=draft.chat_id,
            message_id=draft.message_id,
            status="cancelled",
            source_text=draft.source_text,
            input_source=draft.input_source,
            model_output=draft.model_output,
            expected_output=draft.expected_output,
            issue_summary=draft.issue_summary,
            task_type=draft.task_type,
            scoring_standard=draft.scoring_standard,
            attachments=draft.attachments,
            links=draft.links,
            missing_fields=draft.missing_fields,
            submitted_case_id=draft.submitted_case_id,
            submitted_job_id=draft.submitted_job_id,
            error_message=request.note,
        )
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="badcase_draft_cancelled",
            context=draft.draft_id,
            risk_action="badcase_intake",
        )
        return updated

    def confirm(
        self,
        draft_id: str,
        request: LarkBotBadcaseDraftConfirmRequest,
    ) -> LarkBotBadcaseDraftConfirmResponse:
        repository = self._job_repository()
        draft = repository.get_lark_bot_badcase_draft(draft_id)
        if draft is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}"
            )
        if draft.status == "cancelled":
            raise HTTPException(status_code=409, detail="Badcase draft was cancelled.")
        if draft.missing_fields:
            raise HTTPException(
                status_code=409,
                detail="Badcase draft is missing required fields: "
                + ", ".join(draft.missing_fields),
            )
        if draft.status in {"submitted", "completed"}:
            existing_submitted_job = None
            if draft.submitted_job_id:
                job = repository.get_job(draft.submitted_job_id)
                if job is not None:
                    existing_submitted_job = SubmittedDebugJob(
                        job_id=job.job_id,
                        case_id=job.case_id,
                        status=job.status,
                        artifact_group_id=job.artifact_group_id,
                    )
            return LarkBotBadcaseDraftConfirmResponse(
                draft=draft, submitted_job=existing_submitted_job
            )
        actor = self._resolved_actor(request.actor or draft.actor or draft.open_id)
        submitted_job: SubmittedDebugJob | None = None
        case = self.debug_case_from_draft(draft=draft)
        repository.save_case(case)
        if request.create_job:
            self._raise_if_usage_budget_blocks_submission()
            submitted_job = self._job_service().submit_case_debug(
                case.case_id,
                baseline_trials=0,
                artifact_group_id="lark-bot",
            )
        self.save_sheet_mapping(
            draft=draft,
            case_id=case.case_id,
            job_id=submitted_job.job_id if submitted_job is not None else "",
        )
        updated = repository.save_lark_bot_badcase_draft(
            draft_id=draft.draft_id,
            actor=actor,
            open_id=draft.open_id,
            chat_id=draft.chat_id,
            message_id=draft.message_id,
            status="submitted" if submitted_job is not None else "ready_for_confirmation",
            source_text=draft.source_text,
            input_source=draft.input_source,
            model_output=draft.model_output,
            expected_output=draft.expected_output,
            issue_summary=draft.issue_summary,
            task_type=draft.task_type,
            scoring_standard=draft.scoring_standard,
            attachments=draft.attachments,
            links=draft.links,
            missing_fields=[],
            submitted_case_id=case.case_id,
            submitted_job_id=submitted_job.job_id if submitted_job is not None else "",
        )
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="badcase_draft_confirmed",
            context=draft.draft_id,
            risk_action="debug_job_submission",
        )
        return LarkBotBadcaseDraftConfirmResponse(draft=updated, submitted_job=submitted_job)

    def debug_case_from_draft(self, *, draft: LarkBotBadcaseDraft) -> DebugCase:
        imported_case = _debug_case_from_link_contexts(draft.attachments)
        if imported_case is not None:
            return imported_case
        expected_payload = _json_object_or_text(draft.expected_output)
        media_uri = self.media_uri(draft.input_source)
        prompt = "\n".join(
            [
                "Debug this enterprise badcase.",
                "",
                f"Input source: {draft.input_source}",
                self.media_note(draft.input_source, media_uri),
                f"Observed model output: {draft.model_output}",
                f"Expected output: {draft.expected_output}",
                f"Issue summary: {draft.issue_summary}",
                "",
                "Return the corrected structured output as JSON when possible, then explain the likely root cause.",
            ]
        )
        return DebugCase(
            case_id=f"lark-draft-{safe_path_fragment(draft.draft_id)}",
            task_type=draft.task_type,
            image_uri=media_uri,
            prompt=prompt,
            golden_answer=AnswerSet(answers=[]),
            expected_output={"reference_answer": expected_payload},
            output_schema={},
            scoring_standard=draft.scoring_standard,
            predictions=[Prediction(trial=0, raw_output=draft.model_output, score=0)],
            avg_score=0.0,
            human_notes=HumanNotes(
                debug_status="from_lark_badcase_draft", root_cause=draft.issue_summary
            ),
        )

    def save_sheet_mapping(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        case_id: str,
        job_id: str,
    ) -> None:
        mapping = self.sheet_mapping(draft=draft)
        if not mapping:
            return
        spreadsheet_id, sheet_id, row_id = mapping
        self._job_repository().save_spreadsheet_row_mapping(
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            row_id=row_id,
            case_id=case_id,
            job_id=job_id,
        )

    def sheet_mapping(self, *, draft: LarkBotBadcaseDraft) -> tuple[str, str, str] | None:
        return self.tabular_mapping(draft=draft, link_type="lark_sheet")

    def base_mapping(self, *, draft: LarkBotBadcaseDraft) -> tuple[str, str, str] | None:
        return self.tabular_mapping(draft=draft, link_type="lark_base")

    def tabular_mapping(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        link_type: str = "",
    ) -> tuple[str, str, str] | None:
        for attachment in draft.attachments:
            attachment_link_type = _object_string(attachment, "link_type")
            if link_type and attachment_link_type != link_type:
                continue
            if attachment_link_type == "lark_sheet":
                token = _object_string(attachment, "token")
                sheet_id = _object_string(attachment, "sheet_id")
                selected_row = _object_string(attachment, "selected_row")
                if token and sheet_id and selected_row:
                    return token, sheet_id, selected_row
            if attachment_link_type == "lark_base":
                token = _object_string(attachment, "token")
                table_id = _object_string(attachment, "table_id")
                record_id = _object_string(attachment, "selected_record") or _object_string(
                    attachment, "record_id"
                )
                if token and table_id and record_id:
                    return token, table_id, record_id
        return None

    def media_uri(self, input_source: str) -> str:
        source = input_source.strip()
        if not source:
            return ""
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https", "data", "tos"}:
            return source
        if parsed.scheme == "file":
            return source if self.file_uri_exists(source) else ""
        return ""

    def file_uri_exists(self, uri: str) -> bool:
        parsed = urlparse(uri)
        path_text = unquote(parsed.path)
        if os.name == "nt" and len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        if parsed.netloc:
            path_text = f"//{parsed.netloc}{unquote(parsed.path)}"
        return Path(path_text).exists()

    def media_note(self, input_source: str, media_uri: str) -> str:
        if not input_source.strip():
            return "Media input: not provided."
        if media_uri:
            return f"Media input: attached via {media_uri}."
        return (
            "Media input: not directly accessible to the model; treat the input source as a "
            "sample identifier and reason from the observed output, expected output, issue summary, "
            "and scoring standard."
        )

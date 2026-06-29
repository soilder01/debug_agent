from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import HTTPException
from fastapi.responses import Response

from debug_agent.api.lark_badcase_rendering import LarkBotBadcaseAction
from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCancelRequest,
    LarkBotBadcaseDraftCompletionFailedRequest,
    LarkBotBadcaseDraftCompletionNotifiedRequest,
    LarkBotBadcaseDraftConfirmRequest,
    LarkBotBadcaseDraftConfirmResponse,
)
from debug_agent.lark.bot import LarkBotReplyPayload
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft


class LarkBadcaseActionController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        resolved_actor: Callable[[str], str],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
        confirmation_card_payload: Callable[[LarkBotBadcaseDraft, bool], LarkBotReplyPayload],
        draft_for_action_link: Callable[[str, LarkBotBadcaseAction, str], LarkBotBadcaseDraft],
        action_page_html: Callable[
            [LarkBotBadcaseDraft, Literal["confirm_badcase_draft", "cancel_badcase_draft"], str],
            str,
        ],
        spreadsheet_writeback_page_html: Callable[[LarkBotBadcaseDraft, str], str],
        base_writeback_page_html: Callable[[LarkBotBadcaseDraft, str], str],
        write_spreadsheet: Callable[[LarkBotBadcaseDraft], object],
        write_base: Callable[[LarkBotBadcaseDraft], object],
        action_result_html: Callable[[str, list[str]], str],
        http_exception_detail_text: Callable[[object], str],
        confirm_badcase_draft: Callable[
            [str, LarkBotBadcaseDraftConfirmRequest], LarkBotBadcaseDraftConfirmResponse
        ],
        cancel_badcase_draft: Callable[
            [str, LarkBotBadcaseDraftCancelRequest], LarkBotBadcaseDraft
        ],
        completion_delivery_failure_state: Callable[[str], dict[str, object]],
        completion_delivery_failure_message: Callable[..., str],
    ) -> None:
        self._job_repository = job_repository
        self._resolved_actor = resolved_actor
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit
        self._confirmation_card_payload = confirmation_card_payload
        self._draft_for_action_link = draft_for_action_link
        self._action_page_html = action_page_html
        self._spreadsheet_writeback_page_html = spreadsheet_writeback_page_html
        self._base_writeback_page_html = base_writeback_page_html
        self._write_spreadsheet = write_spreadsheet
        self._write_base = write_base
        self._action_result_html = action_result_html
        self._http_exception_detail_text = http_exception_detail_text
        self._confirm_badcase_draft = confirm_badcase_draft
        self._cancel_badcase_draft = cancel_badcase_draft
        self._completion_delivery_failure_state = completion_delivery_failure_state
        self._completion_delivery_failure_message = completion_delivery_failure_message

    def preview_confirmation_card(self, draft_id: str) -> LarkBotReplyPayload:
        draft = self._draft(draft_id)
        if draft.missing_fields:
            raise HTTPException(
                status_code=409,
                detail="Badcase draft is missing required fields: "
                + ", ".join(draft.missing_fields),
            )
        if draft.status not in {"ready_for_confirmation", "submitted"}:
            raise HTTPException(
                status_code=409,
                detail=f"Badcase draft is not ready for confirmation: {draft.status}",
            )
        return self._confirmation_card_payload(draft, True)

    def preview_confirm_link(
        self,
        draft_id: str,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"],
        token: str,
    ) -> Response:
        draft = self._draft_for_action_link(draft_id, action, token)
        return Response(
            self._action_page_html(draft, action, token),
            media_type="text/html; charset=utf-8",
        )

    def submit_confirm_link(
        self,
        draft_id: str,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"],
        token: str,
    ) -> Response:
        draft = self._draft_for_action_link(draft_id, action, token)
        if action == "confirm_badcase_draft":
            response = self._confirm_badcase_draft(
                draft.draft_id,
                LarkBotBadcaseDraftConfirmRequest(
                    actor=draft.open_id or draft.actor,
                    note="Confirmed from Lark confirmation link.",
                    create_job=True,
                ),
            )
            return Response(
                self._action_result_html(
                    "已提交 Debug 任务",
                    [
                        f"草稿编号：{response.draft.draft_id}",
                        "任务编号："
                        f"{response.submitted_job.job_id if response.submitted_job else response.draft.submitted_job_id}",
                        "可以回到飞书等待小D推送完成通知。",
                    ],
                ),
                media_type="text/html; charset=utf-8",
            )
        cancelled = self._cancel_badcase_draft(
            draft.draft_id,
            LarkBotBadcaseDraftCancelRequest(
                actor=draft.open_id or draft.actor,
                note="Cancelled from Lark confirmation link.",
            ),
        )
        return Response(
            self._action_result_html(
                "已取消 badcase 草稿",
                [f"草稿编号：{cancelled.draft_id}", "这条草稿不会创建 Debug 任务。"],
            ),
            media_type="text/html; charset=utf-8",
        )

    def preview_writeback_link(self, draft_id: str, token: str) -> Response:
        draft = self._draft_for_action_link(draft_id, "writeback_spreadsheet", token)
        return Response(
            self._spreadsheet_writeback_page_html(draft, token),
            media_type="text/html; charset=utf-8",
        )

    def submit_writeback_link(self, draft_id: str, token: str) -> Response:
        draft = self._draft_for_action_link(draft_id, "writeback_spreadsheet", token)
        try:
            result = self._write_spreadsheet(draft)
        except HTTPException as exc:
            return Response(
                self._action_result_html(
                    "表格写回失败",
                    [
                        f"草稿编号：{draft.draft_id}",
                        f"失败原因：{self._http_exception_detail_text(exc.detail)}",
                    ],
                ),
                status_code=exc.status_code,
                media_type="text/html; charset=utf-8",
            )
        return Response(
            self._action_result_html(
                "已写回原表格",
                [
                    f"草稿编号：{draft.draft_id}",
                    f"任务编号：{draft.submitted_job_id}",
                    f"表格行：{getattr(result, 'row_id')}",
                    f"写回字段：{', '.join(getattr(result, 'fields').keys())}",
                ],
            ),
            media_type="text/html; charset=utf-8",
        )

    def preview_base_writeback_link(self, draft_id: str, token: str) -> Response:
        draft = self._draft_for_action_link(draft_id, "writeback_base", token)
        return Response(
            self._base_writeback_page_html(draft, token),
            media_type="text/html; charset=utf-8",
        )

    def submit_base_writeback_link(self, draft_id: str, token: str) -> Response:
        draft = self._draft_for_action_link(draft_id, "writeback_base", token)
        try:
            result = self._write_base(draft)
        except HTTPException as exc:
            return Response(
                self._action_result_html(
                    "Base 写回失败",
                    [
                        f"草稿编号：{draft.draft_id}",
                        f"失败原因：{self._http_exception_detail_text(exc.detail)}",
                    ],
                ),
                status_code=exc.status_code,
                media_type="text/html; charset=utf-8",
            )
        return Response(
            self._action_result_html(
                "已写回 Base 记录",
                [
                    f"草稿编号：{draft.draft_id}",
                    f"任务编号：{draft.submitted_job_id}",
                    f"Base：{getattr(result, 'base_token')}/{getattr(result, 'table_id')}",
                    f"记录：{getattr(result, 'record_id')}",
                    f"写回字段：{', '.join(getattr(result, 'fields').keys())}",
                ],
            ),
            media_type="text/html; charset=utf-8",
        )

    def mark_completion_notified(
        self,
        draft_id: str,
        request: LarkBotBadcaseDraftCompletionNotifiedRequest,
    ) -> LarkBotBadcaseDraft:
        draft, job = self._completed_draft_and_job(draft_id)
        actor = self._resolved_actor(request.actor or draft.actor or draft.open_id)
        updated = self._job_repository().save_lark_bot_badcase_draft(
            draft_id=draft.draft_id,
            actor=actor,
            open_id=draft.open_id,
            chat_id=draft.chat_id,
            message_id=draft.message_id,
            status="completed",
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
            error_message="",
        )
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="badcase_completion_notified",
            context=draft.draft_id,
            risk_action="im_reply",
        )
        self._job_repository().mark_lark_notification_outbox_sent(
            f"badcase-completion:{draft.draft_id}:{job.job_id}"
        )
        return updated

    def mark_completion_delivery_failed(
        self,
        draft_id: str,
        request: LarkBotBadcaseDraftCompletionFailedRequest,
    ) -> LarkBotBadcaseDraft:
        draft, job = self._completed_draft_and_job(draft_id)
        actor = self._resolved_actor(request.actor or draft.actor or draft.open_id)
        state = self._completion_delivery_failure_state(draft.error_message)
        previous_attempts = state.get("attempts", 0)
        attempts = (previous_attempts if isinstance(previous_attempts, int) else 0) + 1
        max_attempts = request.max_attempts
        terminal = attempts >= max_attempts
        updated = self._job_repository().save_lark_bot_badcase_draft(
            draft_id=draft.draft_id,
            actor=actor,
            open_id=draft.open_id,
            chat_id=draft.chat_id,
            message_id=draft.message_id,
            status="completion_delivery_failed" if terminal else draft.status,
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
            error_message=self._completion_delivery_failure_message(
                attempts=attempts,
                max_attempts=max_attempts,
                request=request,
            ),
        )
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation=(
                "badcase_completion_delivery_failed"
                if terminal
                else "badcase_completion_delivery_retry"
            ),
            context=draft.draft_id,
            risk_action="im_reply",
            error_type="im_delivery_failed",
            hint=request.error_message or request.note,
        )
        self._job_repository().mark_lark_notification_outbox_failed(
            f"badcase-completion:{draft.draft_id}:{job.job_id}",
            last_error=request.error_message or request.note or "lark-cli delivery failed",
            terminal=terminal,
        )
        return updated

    def _draft(self, draft_id: str) -> LarkBotBadcaseDraft:
        draft = self._job_repository().get_lark_bot_badcase_draft(draft_id)
        if draft is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}"
            )
        return draft

    def _completed_draft_and_job(self, draft_id: str):
        draft = self._draft(draft_id)
        if not draft.submitted_job_id:
            raise HTTPException(status_code=409, detail="Badcase draft has no submitted job.")
        job = self._job_repository().get_job(draft.submitted_job_id)
        if job is None or job.status != "completed":
            raise HTTPException(status_code=409, detail="Submitted job is not completed yet.")
        return draft, job

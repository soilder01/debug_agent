from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.badcase_intake_parsers import (
    _extract_badcase_fields_from_text,
    _extract_links,
)
from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCancelRequest,
    LarkBotBadcaseDraftConfirmRequest,
    LarkBotBadcaseDraftConfirmResponse,
    LarkBotBadcaseDraftRequest,
)
from debug_agent.assistant.chat import ProjectAssistant
from debug_agent.lark.bot import LarkBotCommandAction, LarkBotCommandRequest, LarkBotCommandResponse
from debug_agent.lark.bot import LarkBotReplyPayload
from debug_agent.lark.xiaod_orchestrator import XiaoDConversationContext, XiaoDTurnDecision
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft
from debug_agent.storage.repository import LarkBotPendingCommand
from debug_agent.xiaod.brain import XiaoDSemanticBrain
from debug_agent.xiaod.handlers import (
    SaveBadcaseDraftInput,
    XiaoDHandlerDependencies,
    handle_xiaod_turn as handle_xiaod_turn_with_dependencies,
)
from debug_agent.xiaod.schemas import (
    XiaoDTurnDecisionResponse,
    XiaoDTurnHandleRequest,
    XiaoDTurnHandleResponse,
)


class XiaoDTurnAdapterController:
    def __init__(
        self,
        *,
        report_base_url: Callable[[], str],
        job_repository: Callable[[], DebugJobRepository],
        project_assistant: Callable[[], ProjectAssistant],
        semantic_brain: Callable[[], XiaoDSemanticBrain | None],
        resolved_actor: Callable[[str], str],
        save_badcase_draft_from_request: Callable[..., LarkBotBadcaseDraft],
        input_source_is_missing_placeholder: Callable[[str], bool],
        confirm_badcase_draft: Callable[
            [str, LarkBotBadcaseDraftConfirmRequest], LarkBotBadcaseDraftConfirmResponse
        ],
        cancel_badcase_draft: Callable[
            [str, LarkBotBadcaseDraftCancelRequest], LarkBotBadcaseDraft
        ],
        confirmation_card_payload: Callable[[LarkBotBadcaseDraft, bool], LarkBotReplyPayload],
        preview_backend_command: Callable[[LarkBotCommandRequest], LarkBotCommandResponse],
        create_pending_command: Callable[[LarkBotCommandResponse, str], LarkBotPendingCommand],
        active_pending_command: Callable[[XiaoDTurnHandleRequest], LarkBotPendingCommand | None],
        continue_pending_command: Callable[
            [LarkBotPendingCommand, XiaoDTurnHandleRequest], LarkBotReplyPayload
        ],
        decline_pending_command: Callable[
            [LarkBotPendingCommand, XiaoDTurnHandleRequest], LarkBotReplyPayload
        ],
        retain_pending_command: Callable[
            [LarkBotPendingCommand, XiaoDTurnHandleRequest], LarkBotReplyPayload
        ],
        delete_pending_command: Callable[
            [LarkBotPendingCommand, XiaoDTurnHandleRequest], LarkBotReplyPayload
        ],
        read_action_summary: Callable[[LarkBotCommandAction], list[str]],
        current_progress_payload: Callable[[XiaoDTurnHandleRequest], LarkBotReplyPayload],
        recent_tasks_payload: Callable[[XiaoDTurnHandleRequest], LarkBotReplyPayload],
        current_job_control_payload: Callable[[XiaoDTurnHandleRequest, str], LarkBotReplyPayload],
        spreadsheet_rerun_writeback_decision: Callable[
            [XiaoDTurnHandleRequest, bool], LarkBotReplyPayload
        ],
        pending_spreadsheet_rerun_writeback_decision: Callable[
            [XiaoDTurnHandleRequest], object | None
        ],
        http_exception_detail_text: Callable[[object], str],
    ) -> None:
        self._report_base_url = report_base_url
        self._job_repository = job_repository
        self._project_assistant = project_assistant
        self._semantic_brain = semantic_brain
        self._resolved_actor = resolved_actor
        self._save_badcase_draft_from_request = save_badcase_draft_from_request
        self._input_source_is_missing_placeholder = input_source_is_missing_placeholder
        self._confirm_badcase_draft = confirm_badcase_draft
        self._cancel_badcase_draft = cancel_badcase_draft
        self._confirmation_card_payload = confirmation_card_payload
        self._preview_backend_command = preview_backend_command
        self._create_pending_command = create_pending_command
        self._active_pending_command = active_pending_command
        self._continue_pending_command = continue_pending_command
        self._decline_pending_command = decline_pending_command
        self._retain_pending_command = retain_pending_command
        self._delete_pending_command = delete_pending_command
        self._read_action_summary = read_action_summary
        self._current_progress_payload = current_progress_payload
        self._recent_tasks_payload = recent_tasks_payload
        self._current_job_control_payload = current_job_control_payload
        self._spreadsheet_rerun_writeback_decision = spreadsheet_rerun_writeback_decision
        self._pending_spreadsheet_rerun_writeback_decision = (
            pending_spreadsheet_rerun_writeback_decision
        )
        self._http_exception_detail_text = http_exception_detail_text

    async def semantic_decision(
        self,
        request: XiaoDTurnHandleRequest,
        context: XiaoDConversationContext | None,
    ) -> XiaoDTurnDecision | None:
        semantic_brain = self._semantic_brain()
        if semantic_brain is None:
            return None
        return await semantic_brain.decide(request, context=context)

    async def handle_turn(
        self,
        request: XiaoDTurnHandleRequest,
        decision: XiaoDTurnDecision,
        decision_response: XiaoDTurnDecisionResponse,
    ) -> XiaoDTurnHandleResponse:
        return await handle_xiaod_turn_with_dependencies(
            request,
            decision,
            decision_response,
            deps=self.handler_dependencies(),
        )

    def handler_dependencies(self) -> XiaoDHandlerDependencies:
        return XiaoDHandlerDependencies(
            report_base_url=self._report_base_url(),
            resolve_actor=self._resolved_actor,
            latest_draft_for_chat=self.latest_draft_for_chat,
            list_ready_drafts=self.ready_badcase_drafts,
            save_badcase_draft=self.save_badcase_draft_from_input,
            confirm_badcase_draft=self.confirm_badcase_draft,
            cancel_badcase_draft=self.cancel_badcase_draft,
            confirmation_card_payload=self.confirmation_card_payload,
            preview_backend_command=self._preview_backend_command,
            create_pending_command=self._create_pending_command,
            active_pending_command=self._active_pending_command,
            continue_pending_command=self._continue_pending_command,
            decline_pending_command=self._decline_pending_command,
            retain_pending_command=self._retain_pending_command,
            delete_pending_command=self._delete_pending_command,
            read_action_summary=self._read_action_summary,
            current_progress_payload=self._current_progress_payload,
            recent_tasks_payload=self._recent_tasks_payload,
            current_job_control_payload=self._current_job_control_payload,
            spreadsheet_rerun_writeback_decision=self._spreadsheet_rerun_writeback_decision,
            assistant_answer=self.assistant_answer,
            error_detail=self.error_detail,
        )

    def conversation_context(self, request: XiaoDTurnHandleRequest) -> XiaoDConversationContext:
        repository = self._job_repository()
        open_draft = (
            repository.latest_lark_bot_badcase_draft_for_chat(
                chat_id=request.chat_id,
                open_id=request.open_id,
            )
            if request.chat_id
            else None
        )
        submitted_draft = self.latest_submitted_draft_for_chat(
            chat_id=request.chat_id,
            open_id=request.open_id,
        )
        latest_job_id = submitted_draft.submitted_job_id if submitted_draft is not None else ""
        latest_job = repository.get_job(latest_job_id) if latest_job_id else None
        report_url = ""
        if latest_job is not None:
            report_document = repository.get_lark_report_document(latest_job.job_id)
            if (
                report_document is not None
                and report_document.status == "published"
                and report_document.document_url
            ):
                report_url = report_document.document_url
        return XiaoDConversationContext(
            has_open_draft=open_draft is not None,
            has_ready_draft=open_draft is not None
            and open_draft.status == "ready_for_confirmation",
            latest_open_draft_status=open_draft.status if open_draft is not None else "",
            latest_submitted_job_id=latest_job.job_id if latest_job is not None else latest_job_id,
            latest_submitted_job_status=latest_job.status if latest_job is not None else "",
            latest_report_url=report_url,
            has_pending_command=self._active_pending_command(request) is not None,
            has_pending_writeback_decision=(
                self._pending_spreadsheet_rerun_writeback_decision(request) is not None
            ),
        )

    async def assistant_answer(self, question: str, model_id: str) -> str:
        answer = await self._project_assistant().answer(question, model_id=model_id)
        return answer.answer

    def latest_draft_for_chat(
        self,
        *,
        chat_id: str,
        open_id: str,
    ) -> LarkBotBadcaseDraft | None:
        repository = self._job_repository()
        open_draft = repository.latest_lark_bot_badcase_draft_for_chat(
            chat_id=chat_id,
            open_id=open_id,
        )
        submitted_draft = self.latest_submitted_draft_for_chat(chat_id=chat_id, open_id=open_id)
        if submitted_draft is None or not submitted_draft.submitted_job_id:
            return open_draft if open_draft is not None else submitted_draft
        job = repository.get_job(submitted_draft.submitted_job_id)
        if job is None or job.status in {"completed", "failed", "cancelled"}:
            return open_draft
        return submitted_draft

    def ready_badcase_drafts(self) -> list[LarkBotBadcaseDraft]:
        return self._job_repository().list_lark_bot_badcase_drafts(
            status="ready_for_confirmation",
            limit=50,
        )

    def latest_submitted_draft_for_chat(
        self,
        *,
        chat_id: str,
        open_id: str,
    ) -> LarkBotBadcaseDraft | None:
        if not chat_id:
            return None
        for draft in self._job_repository().list_lark_bot_badcase_drafts(limit=200):
            if draft.chat_id != chat_id:
                continue
            if open_id and draft.open_id != open_id:
                continue
            if draft.submitted_job_id:
                return draft
        return None

    def save_badcase_draft_from_input(
        self,
        input_data: SaveBadcaseDraftInput,
        actor: str,
        existing: LarkBotBadcaseDraft | None,
    ) -> LarkBotBadcaseDraft:
        target_existing = (
            None
            if self.should_start_new_badcase_draft(input_data=input_data, existing=existing)
            else existing
        )
        draft = self._save_badcase_draft_from_request(
            request=LarkBotBadcaseDraftRequest(
                actor=input_data.actor,
                open_id=input_data.open_id,
                chat_id=input_data.chat_id,
                message_id=input_data.message_id,
                text=input_data.text,
                input_source=input_data.input_source,
                model_output=input_data.model_output,
                expected_output=input_data.expected_output,
                issue_summary=input_data.issue_summary,
                task_type=input_data.task_type or "generic_json",
                scoring_standard=input_data.scoring_standard,
                attachments=input_data.attachments,
                resolve_link_content=input_data.resolve_link_content,
            ),
            actor=actor,
            draft_id=target_existing.draft_id if target_existing is not None else str(uuid4()),
            existing=target_existing,
        )
        if target_existing is not None and target_existing.submitted_job_id:
            self._job_repository().save_debug_run_stage(
                job_id=target_existing.submitted_job_id,
                stage="supplemental_context",
                status="completed",
                input={
                    "supplement_text": input_data.text,
                    "attachments": input_data.attachments,
                    "actor": actor,
                },
                output={
                    "draft_id": draft.draft_id,
                    "job_id": target_existing.submitted_job_id,
                    "message_id": input_data.message_id,
                    "attachment_count": len(input_data.attachments),
                },
                failure_reason="",
                retryable=False,
            )
        return draft

    def should_start_new_badcase_draft(
        self,
        *,
        input_data: SaveBadcaseDraftInput,
        existing: LarkBotBadcaseDraft | None,
    ) -> bool:
        if existing is None:
            return False
        text = input_data.text.strip()
        if not text:
            return False
        if existing.submitted_job_id:
            return not self.is_explicit_badcase_supplement(text)
        if existing.status != "ready_for_confirmation" and not existing.submitted_job_id:
            return False
        extracted = _extract_badcase_fields_from_text(text)
        semantic_input_source = (
            ""
            if self._input_source_is_missing_placeholder(input_data.input_source)
            else input_data.input_source
        )
        has_fresh_input = bool(
            semantic_input_source
            or extracted["input_source"]
            or _extract_links(text)
            or input_data.attachments
        )
        has_fresh_result = any(
            getattr(input_data, field) or extracted[field]
            for field in ("model_output", "expected_output", "issue_summary")
        )
        lowered = text.lower()
        has_badcase_marker = "badcase" in lowered or any(
            marker in text
            for marker in (
                "原始输入",
                "模型输出",
                "正确答案",
                "期望结果",
                "错误现象",
                "识别错",
                "识别错误",
            )
        )
        semantic_has_case_fields = bool(semantic_input_source and has_fresh_result)
        return (
            (has_badcase_marker or semantic_has_case_fields)
            and has_fresh_input
            and (has_fresh_result or bool(_extract_links(text)))
        )

    @staticmethod
    def is_explicit_badcase_supplement(text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith(
            (
                "补充材料",
                "补充一下",
                "补充信息",
                "追加材料",
                "追加信息",
                "再补充",
            )
        )

    def confirm_badcase_draft(
        self,
        draft_id: str,
        actor: str,
    ) -> LarkBotBadcaseDraftConfirmResponse:
        return self._confirm_badcase_draft(
            draft_id,
            LarkBotBadcaseDraftConfirmRequest(
                actor=actor,
                note="Confirmed from Lark conversation.",
                create_job=True,
            ),
        )

    def cancel_badcase_draft(
        self,
        draft_id: str,
        actor: str,
    ) -> LarkBotBadcaseDraft:
        return self._cancel_badcase_draft(
            draft_id,
            LarkBotBadcaseDraftCancelRequest(
                actor=actor,
                note="Cancelled from Lark conversation.",
            ),
        )

    def confirmation_card_payload(
        self,
        draft: LarkBotBadcaseDraft,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotReplyPayload:
        targeted_draft = draft.model_copy(
            update={
                "message_id": request.message_id or draft.message_id,
                "chat_id": request.chat_id or draft.chat_id,
                "open_id": request.open_id or draft.open_id,
            }
        )
        return self._confirmation_card_payload(targeted_draft, False)

    def error_detail(self, exc: Exception) -> str:
        if isinstance(exc, HTTPException):
            return self._http_exception_detail_text(exc.detail)
        return str(exc)[:300]

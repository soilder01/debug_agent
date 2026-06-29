from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import pytest

from debug_agent.lark.bot import (
    LarkBotCommandRequest,
    LarkBotCommandResponse,
    LarkBotReplyPayload,
)
from debug_agent.lark.xiaod_orchestrator import XiaoDTurnDecision
from debug_agent.xiaod.handlers import (
    SaveBadcaseDraftInput,
    XiaoDHandlerDependencies,
    handle_xiaod_turn,
)
from debug_agent.xiaod.schemas import (
    XiaoDTurnDecisionResponse,
    XiaoDTurnHandleRequest,
)


@dataclass
class DraftView:
    draft_id: str = "draft-1"
    status: str = "needs_more_info"
    missing_fields: list[str] = field(default_factory=list)
    attachments: list[dict[str, object]] = field(default_factory=list)
    input_source: str = ""
    model_output: str = ""
    expected_output: str = ""
    issue_summary: str = ""
    submitted_case_id: str = ""
    submitted_job_id: str = ""
    chat_id: str = "oc_1"
    open_id: str = "ou_1"


@dataclass
class SubmittedJobView:
    job_id: str = "job-1"
    status: str = "submitted"


@dataclass
class ConfirmResponseView:
    draft: DraftView = field(default_factory=DraftView)
    submitted_job: SubmittedJobView | None = None


@dataclass
class PendingCommandView:
    command_id: str = "pending-1"
    action_kind: str = "spreadsheet_rerun"
    command_text: str = "/debug spreadsheet rerun"
    status: str = "pending"
    action: dict[str, object] = field(default_factory=dict)


@pytest.mark.asyncio
async def test_save_draft_backend_failure_returns_deliverable_reply() -> None:
    async def assistant_answer(question: str, model_id: str) -> str:
        return f"answer {question} {model_id}"

    def save_badcase_draft(
        input_data: SaveBadcaseDraftInput,
        actor: str,
        existing: DraftView | None,
    ) -> DraftView:
        raise RuntimeError("repository down")

    response = await handle_xiaod_turn(
        _request(text="帮我调试这个 badcase"),
        XiaoDTurnDecision(kind="save_badcase_draft", clean_text="帮我调试这个 badcase"),
        _decision_response("save_badcase_draft"),
        deps=_deps(
            assistant_answer=assistant_answer,
            save_badcase_draft=save_badcase_draft,
        ),
    )

    assert response.handled is True
    assert response.reply is not None
    assert response.reply.target_type == "message"
    assert "记录 badcase 草稿失败：repository down" in response.reply.markdown


@pytest.mark.asyncio
async def test_backend_command_preview_failure_returns_deliverable_reply() -> None:
    async def assistant_answer(question: str, model_id: str) -> str:
        return f"answer {question} {model_id}"

    def preview_backend_command(request: LarkBotCommandRequest) -> LarkBotCommandResponse:
        raise RuntimeError("preview down")

    response = await handle_xiaod_turn(
        _request(text="/debug jobs"),
        XiaoDTurnDecision(
            kind="backend_command",
            clean_text="/debug jobs",
            backend_command="/debug jobs",
        ),
        _decision_response("backend_command", backend_command="/debug jobs"),
        deps=_deps(
            assistant_answer=assistant_answer,
            preview_backend_command=preview_backend_command,
        ),
    )

    assert response.handled is True
    assert response.reply is not None
    assert response.reply.target_type == "message"
    assert "处理 Debug Agent 命令失败：preview down" in response.reply.markdown


@pytest.mark.asyncio
async def test_current_progress_query_returns_deliverable_reply() -> None:
    async def assistant_answer(question: str, model_id: str) -> str:
        return f"answer {question} {model_id}"

    response = await handle_xiaod_turn(
        _request(text="现在跑到哪了？"),
        XiaoDTurnDecision(
            kind="query_current_progress",
            clean_text="现在跑到哪了？",
            reason="current_debug_progress",
        ),
        _decision_response("query_current_progress"),
        deps=_deps(
            assistant_answer=assistant_answer,
            current_progress_payload=lambda request: LarkBotReplyPayload(
                command_id="progress-1",
                action_kind="query_current_progress",
                status="handled",
                target_type="message",
                message_id=request.message_id,
                markdown="当前任务正在执行基础复测。",
                message_type="interactive",
                content={"header": {"title": {"content": "当前任务进度"}}},
                idempotency_key="progress-key",
            ),
        ),
    )

    assert response.handled is True
    assert response.reply is not None
    assert response.reply.target_type == "message"
    assert response.reply.action_kind == "query_current_progress"
    assert response.reply.message_type == "interactive"
    assert "当前任务正在执行基础复测。" in response.reply.markdown


@pytest.mark.asyncio
async def test_recent_tasks_query_returns_interactive_payload() -> None:
    async def assistant_answer(question: str, model_id: str) -> str:
        return f"answer {question} {model_id}"

    response = await handle_xiaod_turn(
        _request(text="最近 3 个任务"),
        XiaoDTurnDecision(
            kind="query_recent_tasks",
            clean_text="最近 3 个任务",
            reason="recent_debug_tasks",
        ),
        _decision_response("query_recent_tasks"),
        deps=_deps(
            assistant_answer=assistant_answer,
            recent_tasks_payload=lambda request: LarkBotReplyPayload(
                command_id="recent-1",
                action_kind="query_recent_tasks",
                status="handled",
                target_type="message",
                message_id=request.message_id,
                markdown="最近 Debug 任务",
                message_type="interactive",
                content={"header": {"title": {"content": "最近 Debug 任务"}}},
                idempotency_key="recent-key",
            ),
        ),
    )

    assert response.handled is True
    assert response.reply is not None
    assert response.reply.action_kind == "query_recent_tasks"
    assert response.reply.message_type == "interactive"
    assert response.reply.content["header"]["title"]["content"] == "最近 Debug 任务"


@pytest.mark.asyncio
async def test_assistant_failure_returns_deliverable_reply() -> None:
    async def assistant_answer(question: str, model_id: str) -> str:
        raise RuntimeError("assistant down")

    response = await handle_xiaod_turn(
        _request(text="解释一下报告"),
        XiaoDTurnDecision(
            kind="assistant_chat",
            clean_text="解释一下报告",
            assistant_question="解释一下报告",
        ),
        _decision_response("assistant_chat"),
        deps=_deps(assistant_answer=assistant_answer),
    )

    assert response.handled is True
    assert response.reply is not None
    assert response.reply.target_type == "message"
    assert "回答失败：assistant down" in response.reply.markdown


def _request(*, text: str) -> XiaoDTurnHandleRequest:
    return XiaoDTurnHandleRequest(
        text=text,
        actor="ou_1",
        open_id="ou_1",
        chat_id="oc_1",
        message_id="om_1",
    )


def _decision_response(
    kind: str,
    *,
    backend_command: str = "",
) -> XiaoDTurnDecisionResponse:
    return XiaoDTurnDecisionResponse(
        kind=kind,  # type: ignore[arg-type]
        clean_text="",
        backend_command=backend_command,
    )


def _deps(
    *,
    assistant_answer: Callable[[str, str], Awaitable[str]],
    save_badcase_draft: Callable[
        [SaveBadcaseDraftInput, str, DraftView | None],
        DraftView,
    ]
    | None = None,
    preview_backend_command: Callable[[LarkBotCommandRequest], LarkBotCommandResponse]
    | None = None,
    current_progress_payload: Callable[[XiaoDTurnHandleRequest], LarkBotReplyPayload] | None = None,
    recent_tasks_payload: Callable[[XiaoDTurnHandleRequest], LarkBotReplyPayload] | None = None,
    current_job_control_payload: Callable[[XiaoDTurnHandleRequest, str], LarkBotReplyPayload]
    | None = None,
    spreadsheet_rerun_writeback_decision: Callable[
        [XiaoDTurnHandleRequest, bool], LarkBotReplyPayload
    ]
    | None = None,
) -> XiaoDHandlerDependencies:
    return XiaoDHandlerDependencies(
        report_base_url="http://debug-agent.local",
        resolve_actor=lambda actor: actor or "system",
        latest_draft_for_chat=lambda *, chat_id, open_id: None,
        list_ready_drafts=lambda: [],
        save_badcase_draft=save_badcase_draft or _save_badcase_draft,
        confirm_badcase_draft=lambda draft_id, actor: ConfirmResponseView(),
        cancel_badcase_draft=lambda draft_id, actor: DraftView(status="cancelled"),
        confirmation_card_payload=_confirmation_card_payload,
        preview_backend_command=preview_backend_command or _preview_backend_command,
        create_pending_command=lambda preview, note: PendingCommandView(),
        active_pending_command=lambda request: None,
        continue_pending_command=_pending_lifecycle_payload,
        decline_pending_command=_pending_lifecycle_payload,
        retain_pending_command=_pending_lifecycle_payload,
        delete_pending_command=_pending_lifecycle_payload,
        read_action_summary=lambda action: [],
        current_progress_payload=current_progress_payload or _current_progress_payload,
        recent_tasks_payload=recent_tasks_payload or _recent_tasks_payload,
        current_job_control_payload=current_job_control_payload or _current_job_control_payload,
        spreadsheet_rerun_writeback_decision=(
            spreadsheet_rerun_writeback_decision
            or _spreadsheet_rerun_writeback_decision_payload
        ),
        assistant_answer=assistant_answer,
        error_detail=lambda exc: str(exc),
    )


def _save_badcase_draft(
    input_data: SaveBadcaseDraftInput,
    actor: str,
    existing: DraftView | None,
) -> DraftView:
    return DraftView()


def _confirmation_card_payload(
    draft: DraftView,
    request: XiaoDTurnHandleRequest,
) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id="card-1",
        action_kind="save_badcase_draft",
        status="ready_for_confirmation",
        target_type="message",
        message_id=request.message_id,
        markdown="confirm",
        idempotency_key="card-key",
    )


def _preview_backend_command(request: LarkBotCommandRequest) -> LarkBotCommandResponse:
    raise AssertionError("preview_backend_command should not be called")


def _current_progress_payload(request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id="progress-empty",
        action_kind="query_current_progress",
        status="handled",
        target_type="message",
        message_id=request.message_id,
        markdown="没有当前任务。",
        idempotency_key="progress-empty-key",
    )


def _recent_tasks_payload(request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id="recent-empty",
        action_kind="query_recent_tasks",
        status="handled",
        target_type="message",
        message_id=request.message_id,
        markdown="最近 Debug 任务为空。",
        idempotency_key="recent-empty-key",
    )


def _current_job_control_payload(
    request: XiaoDTurnHandleRequest,
    operation: str,
) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id=f"{operation}-job-1",
        action_kind=f"{operation}_current_job",
        status="handled",
        target_type="message",
        message_id=request.message_id,
        markdown=f"{operation} 当前任务。",
        idempotency_key=f"{operation}-job-key",
    )


def _spreadsheet_rerun_writeback_decision_payload(
    request: XiaoDTurnHandleRequest,
    sync_requested: bool,
) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id="writeback-decision-1",
        action_kind="spreadsheet_rerun_writeback_decision",
        status="handled",
        target_type="message",
        message_id=request.message_id,
        markdown=f"sync_requested={sync_requested}",
        idempotency_key="writeback-decision-key",
    )


def _pending_lifecycle_payload(
    pending: PendingCommandView,
    request: XiaoDTurnHandleRequest,
) -> LarkBotReplyPayload:
    return LarkBotReplyPayload(
        command_id=pending.command_id,
        action_kind="pending_lifecycle",
        status=pending.status,
        target_type="message",
        message_id=request.message_id,
        markdown=f"handled {pending.command_id}",
        idempotency_key="pending-lifecycle-key",
    )

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from debug_agent.lark.bot import (
    LarkBotCommandAction,
    LarkBotCommandRequest,
    LarkBotCommandResponse,
    LarkBotReplyPayload,
)
from debug_agent.lark.xiaod_orchestrator import XiaoDTurnDecision
from debug_agent.xiaod.presenter import (
    BadcaseConfirmResponseView,
    BadcaseDraftView,
    PendingCommandView,
    backend_command_markdown,
    badcase_cancelled_markdown,
    badcase_confirmed_markdown,
    badcase_draft_saved_markdown,
    badcase_draft_status_markdown,
    clarify_intent_markdown,
    help_markdown,
    help_card,
    pending_command_continuation_reply_payload,
    pending_command_reply_payload,
    turn_reply_payload,
)
from debug_agent.xiaod.schemas import (
    XiaoDTurnDecisionResponse,
    XiaoDTurnHandleRequest,
    XiaoDTurnHandleResponse,
)


class DraftLookup(Protocol):
    def __call__(self, *, chat_id: str, open_id: str) -> BadcaseDraftView | None: ...


class CurrentProgressPayload(Protocol):
    def __call__(self, request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload: ...


class RecentTasksPayload(Protocol):
    def __call__(self, request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload: ...


class CurrentJobControlPayload(Protocol):
    def __call__(self, request: XiaoDTurnHandleRequest, operation: str) -> LarkBotReplyPayload: ...


@dataclass(frozen=True)
class SaveBadcaseDraftInput:
    actor: str
    open_id: str
    chat_id: str
    message_id: str
    text: str
    attachments: list[dict[str, object]]
    resolve_link_content: bool
    input_source: str = ""
    model_output: str = ""
    expected_output: str = ""
    issue_summary: str = ""
    task_type: str = ""
    scoring_standard: str = ""


@dataclass(frozen=True)
class XiaoDHandlerDependencies:
    report_base_url: str
    resolve_actor: Callable[[str], str]
    latest_draft_for_chat: DraftLookup
    list_ready_drafts: Callable[[], Sequence[BadcaseDraftView]]
    save_badcase_draft: Callable[
        [SaveBadcaseDraftInput, str, BadcaseDraftView | None],
        BadcaseDraftView,
    ]
    confirm_badcase_draft: Callable[[str, str], BadcaseConfirmResponseView]
    cancel_badcase_draft: Callable[[str, str], BadcaseDraftView]
    confirmation_card_payload: Callable[
        [BadcaseDraftView, XiaoDTurnHandleRequest],
        LarkBotReplyPayload,
    ]
    preview_backend_command: Callable[[LarkBotCommandRequest], LarkBotCommandResponse]
    create_pending_command: Callable[
        [LarkBotCommandResponse, str],
        PendingCommandView,
    ]
    active_pending_command: Callable[[XiaoDTurnHandleRequest], PendingCommandView | None]
    continue_pending_command: Callable[
        [PendingCommandView, XiaoDTurnHandleRequest], LarkBotReplyPayload
    ]
    decline_pending_command: Callable[
        [PendingCommandView, XiaoDTurnHandleRequest], LarkBotReplyPayload
    ]
    retain_pending_command: Callable[
        [PendingCommandView, XiaoDTurnHandleRequest], LarkBotReplyPayload
    ]
    delete_pending_command: Callable[
        [PendingCommandView, XiaoDTurnHandleRequest], LarkBotReplyPayload
    ]
    read_action_summary: Callable[[LarkBotCommandAction], Sequence[str]]
    current_progress_payload: CurrentProgressPayload
    recent_tasks_payload: RecentTasksPayload
    current_job_control_payload: CurrentJobControlPayload
    spreadsheet_rerun_writeback_decision: Callable[
        [XiaoDTurnHandleRequest, bool], LarkBotReplyPayload
    ]
    assistant_answer: Callable[[str, str], Awaitable[str]]
    error_detail: Callable[[Exception], str]


async def handle_xiaod_turn(
    request: XiaoDTurnHandleRequest,
    decision: XiaoDTurnDecision,
    decision_response: XiaoDTurnDecisionResponse,
    *,
    deps: XiaoDHandlerDependencies,
) -> XiaoDTurnHandleResponse:
    if decision.kind == "help":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=turn_reply_payload(
                request=request,
                action_kind=decision.kind,
                markdown=help_markdown(),
                message_type="interactive",
                content=help_card(report_base_url=deps.report_base_url),
            ),
        )
    if decision.kind == "badcase_draft_followup":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_badcase_draft_followup_payload(request=request, deps=deps),
        )
    if decision.kind == "query_current_progress":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_current_progress_payload(request=request, deps=deps),
        )
    if decision.kind == "query_recent_tasks":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_recent_tasks_payload(request=request, deps=deps),
        )
    if decision.kind in {"cancel_current_job", "pause_current_job", "resume_current_job"}:
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_current_job_control_payload(
                request=request,
                deps=deps,
                operation=decision.kind.removesuffix("_current_job"),
            ),
        )
    if decision.kind in {
        "continue_pending_command",
        "decline_pending_command",
        "retain_pending_command",
        "delete_pending_command",
    }:
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_pending_command_lifecycle_payload(
                request=request,
                deps=deps,
                operation=decision.kind.removesuffix("_pending_command"),
            ),
        )
    if decision.kind in {"sync_writeback_decision", "skip_writeback_decision"}:
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_spreadsheet_rerun_writeback_decision_payload(
                request=request,
                deps=deps,
                sync_requested=decision.kind == "sync_writeback_decision",
            ),
        )
    if decision.kind == "confirm_badcase_draft":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_confirm_badcase_draft_payload(request=request, deps=deps),
        )
    if decision.kind == "cancel_badcase_draft":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_cancel_badcase_draft_payload(request=request, deps=deps),
        )
    if decision.kind == "save_badcase_draft":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_save_badcase_draft_payload(
                request=request,
                text=decision.clean_text,
                extracted_fields=decision.extracted_fields,
                deps=deps,
            ),
        )
    if decision.kind == "badcase_intake_guidance":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_badcase_intake_guidance_payload(request=request, deps=deps),
        )
    if decision.kind == "backend_command":
        return XiaoDTurnHandleResponse(
            decision=decision_response,
            handled=True,
            reply=_backend_command_payload(
                request=request,
                command_text=decision.backend_command,
                deps=deps,
            ),
        )
    if decision.kind == "clarify_intent":
        return _handled(
            request=request,
            decision_response=decision_response,
            action_kind=decision.kind,
            markdown=clarify_intent_markdown(reason=decision.reason),
        )
    if decision.kind == "assistant_chat":
        try:
            answer = await deps.assistant_answer(
                decision.assistant_question or decision.clean_text,
                decision.assistant_model_id,
            )
        except Exception as exc:
            return _handled(
                request=request,
                decision_response=decision_response,
                action_kind=decision.kind,
                markdown=f"回答失败：{deps.error_detail(exc)}",
            )
        return _handled(
            request=request,
            decision_response=decision_response,
            action_kind=decision.kind,
            markdown=answer,
        )
    return XiaoDTurnHandleResponse(decision=decision_response, handled=False)


def _handled(
    *,
    request: XiaoDTurnHandleRequest,
    decision_response: XiaoDTurnDecisionResponse,
    action_kind: str,
    markdown: str,
) -> XiaoDTurnHandleResponse:
    return XiaoDTurnHandleResponse(
        decision=decision_response,
        handled=True,
        reply=turn_reply_payload(
            request=request,
            action_kind=action_kind,
            markdown=markdown,
        ),
    )


def _badcase_draft_followup_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    draft = (
        deps.latest_draft_for_chat(chat_id=request.chat_id, open_id=request.open_id)
        if request.chat_id
        else None
    )
    if draft is None:
        return turn_reply_payload(
            request=request,
            action_kind="badcase_draft_followup",
            markdown=(
                "我在当前会话里没有找到进行中的 badcase 草稿。\n\n"
                "你可以直接发飞书表格/Base/文档链接，或用自然语言描述要 debug 的问题。"
            ),
        )
    if draft.status == "ready_for_confirmation" and not draft.missing_fields:
        return deps.confirmation_card_payload(draft, request)
    return turn_reply_payload(
        request=request,
        action_kind="badcase_draft_followup",
        markdown=badcase_draft_status_markdown(draft=draft),
    )


def _current_progress_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    try:
        return deps.current_progress_payload(request)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="query_current_progress",
            markdown=f"查询当前任务进度失败：{deps.error_detail(exc)}",
        )


def _recent_tasks_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    try:
        return deps.recent_tasks_payload(request)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="query_recent_tasks",
            markdown=f"查询最近任务失败：{deps.error_detail(exc)}",
        )


def _current_job_control_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
    operation: str,
) -> LarkBotReplyPayload:
    try:
        return deps.current_job_control_payload(request, operation)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind=f"{operation}_current_job",
            markdown=f"处理当前任务失败：{deps.error_detail(exc)}",
        )


def _confirm_badcase_draft_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    draft = _latest_ready_badcase_draft(request=request, deps=deps)
    if draft is None:
        return turn_reply_payload(
            request=request,
            action_kind="confirm_badcase_draft",
            markdown="我还没有找到可提交的 badcase 草稿。请先把要 debug 的问题、链接或附件发给我。",
        )
    try:
        response = deps.confirm_badcase_draft(draft.draft_id, request.actor or request.open_id)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="confirm_badcase_draft",
            markdown=f"提交草稿失败：{deps.error_detail(exc)}",
        )
    return turn_reply_payload(
        request=request,
        action_kind="confirm_badcase_draft",
        markdown=badcase_confirmed_markdown(response=response),
    )


def _cancel_badcase_draft_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    draft = _latest_open_badcase_draft(request=request, deps=deps)
    if draft is None:
        return turn_reply_payload(
            request=request,
            action_kind="cancel_badcase_draft",
            markdown="我还没有找到可取消的 badcase 草稿。",
        )
    try:
        cancelled = deps.cancel_badcase_draft(draft.draft_id, request.actor or request.open_id)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="cancel_badcase_draft",
            markdown=f"取消草稿失败：{deps.error_detail(exc)}",
        )
    return turn_reply_payload(
        request=request,
        action_kind="cancel_badcase_draft",
        markdown=badcase_cancelled_markdown(draft=cancelled),
    )


def _save_badcase_draft_payload(
    *,
    request: XiaoDTurnHandleRequest,
    text: str,
    extracted_fields: dict[str, str],
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    try:
        actor = deps.resolve_actor(request.actor or request.open_id)
        existing = (
            deps.latest_draft_for_chat(chat_id=request.chat_id, open_id=request.open_id)
            if request.chat_id
            else None
        )
        if _is_ready_draft_guidance_request(existing=existing, text=text, request=request):
            return turn_reply_payload(
                request=request,
                action_kind="badcase_draft_guidance",
                markdown=_ready_draft_guidance_markdown(existing),
            )
        draft = deps.save_badcase_draft(
            SaveBadcaseDraftInput(
                actor=actor,
                open_id=request.open_id,
                chat_id=request.chat_id,
                message_id=request.message_id,
                text=text,
                input_source=extracted_fields.get("input_source", ""),
                model_output=extracted_fields.get("model_output", ""),
                expected_output=extracted_fields.get("expected_output", ""),
                issue_summary=extracted_fields.get("issue_summary", ""),
                task_type=extracted_fields.get("task_type", ""),
                scoring_standard=extracted_fields.get("scoring_standard", ""),
                attachments=request.attachments,
                resolve_link_content=request.resolve_link_content,
            ),
            actor,
            existing,
        )
        if (
            existing is not None
            and existing.submitted_job_id
            and draft.draft_id == existing.draft_id
        ):
            return turn_reply_payload(
                request=request,
                action_kind="supplement_current_job",
                markdown=(
                    "已补充到当前 Debug 任务。\n\n"
                    f"- 草稿编号：`{draft.draft_id}`\n"
                    f"- 任务编号：`{existing.submitted_job_id}`\n"
                    "- 我会把这条补充作为当前任务的上下文记录，后续报告和复核可以追溯。"
                ),
            )
        if draft.status == "ready_for_confirmation" and not draft.missing_fields:
            return deps.confirmation_card_payload(draft, request)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="save_badcase_draft",
            markdown=f"记录 badcase 草稿失败：{deps.error_detail(exc)}",
        )
    return turn_reply_payload(
        request=request,
        action_kind="save_badcase_draft",
        markdown=badcase_draft_saved_markdown(draft=draft),
    )


def _badcase_intake_guidance_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    draft = (
        deps.latest_draft_for_chat(chat_id=request.chat_id, open_id=request.open_id)
        if request.chat_id
        else None
    )
    return turn_reply_payload(
        request=request,
        action_kind="badcase_intake_guidance",
        markdown=_ready_draft_guidance_markdown(draft)
        if draft is not None and draft.status == "ready_for_confirmation"
        else _new_badcase_guidance_markdown(),
    )


def _is_ready_draft_guidance_request(
    *,
    existing: BadcaseDraftView | None,
    text: str,
    request: XiaoDTurnHandleRequest,
) -> bool:
    if existing is None or existing.status != "ready_for_confirmation" or existing.submitted_job_id:
        return False
    if request.attachments or "http://" in text or "https://" in text:
        return False
    compact = text.replace(" ", "").lower()
    if any(
        marker in compact
        for marker in (
            "原始输入",
            "模型输出",
            "正确答案",
            "期望结果",
            "错误现象",
            "补充材料",
            "再补充",
        )
    ):
        return False
    return any(
        marker in compact for marker in ("怎么提", "怎么发", "哪些信息", "什么信息", "告诉我")
    )


def _ready_draft_guidance_markdown(draft: BadcaseDraftView | None) -> str:
    if draft is None:
        return _new_badcase_guidance_markdown()
    return "\n".join(
        [
            "你现在有一个待确认的 badcase 草稿，我不会把这句话写进去污染草稿。",
            "",
            f"- 草稿编号：`{draft.draft_id}`",
            "",
            "如果说的是这个草稿：",
            "- 回复 `确认提交`：创建 Debug 任务",
            "- 回复 `取消草稿`：放弃它",
            "- 回复 `补充材料：...`：补充当前任务信息",
            "",
            "如果是新的 case，直接发这四类信息就行：",
            "- 原始输入：图片/视频/文档/表格/Base 链接",
            "- 模型输出：模型实际答了什么",
            "- 正确答案：你认为应该是什么",
            "- 错误现象：错在哪里、影响是什么",
        ]
    )


def _new_badcase_guidance_markdown() -> str:
    return "\n".join(
        [
            "可以，直接把问题当成 badcase 发给我，不需要先整理成固定表单。",
            "",
            "最有用的是这四类信息：",
            "- 原始输入：图片/视频/文档/表格/Base 链接，或直接描述输入",
            "- 模型输出：模型实际答了什么",
            "- 正确答案：你认为应该是什么",
            "- 错误现象：错在哪里、影响是什么",
            "",
            "你可以这样发：",
            "原始输入：https://example.com/a.png；模型输出：3；正确答案：8；错误现象：把 8 识别成 3。",
            "",
            "如果只有一部分信息也可以先发，我会先建草稿并告诉你还缺什么；确认前不会创建 Debug 任务。",
        ]
    )


def _backend_command_payload(
    *,
    request: XiaoDTurnHandleRequest,
    command_text: str,
    deps: XiaoDHandlerDependencies,
) -> LarkBotReplyPayload:
    try:
        preview = deps.preview_backend_command(
            LarkBotCommandRequest(
                text=command_text,
                actor=request.actor,
                open_id=request.open_id,
                chat_id=request.chat_id,
                message_id=request.message_id,
                tenant_key=request.tenant_key,
                identity=request.identity,
                profile=request.profile,
            )
        )
        pending: PendingCommandView | None = None
        if preview.action.confirmation_required:
            existing = deps.active_pending_command(request)
            if existing is not None:
                return pending_command_continuation_reply_payload(
                    request=request,
                    pending=existing,
                    report_base_url=deps.report_base_url,
                )
            pending = deps.create_pending_command(preview, "Created from XiaoD turn handle.")
            return pending_command_reply_payload(
                request=request,
                preview=preview,
                pending=pending,
                report_base_url=deps.report_base_url,
            )
        markdown = backend_command_markdown(
            preview=preview,
            read_summary_lines=deps.read_action_summary(preview.action),
        )
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind="backend_command",
            markdown=f"处理 Debug Agent 命令失败：{deps.error_detail(exc)}",
        )
    return turn_reply_payload(
        request=request,
        action_kind=preview.action.kind,
        markdown=markdown,
    )


def _pending_command_lifecycle_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
    operation: str,
) -> LarkBotReplyPayload:
    pending = deps.active_pending_command(request)
    if pending is None:
        return turn_reply_payload(
            request=request,
            action_kind=f"{operation}_pending_command",
            markdown="我在当前会话里没有找到你的未执行小D待确认操作。",
        )
    try:
        if operation == "continue":
            return deps.continue_pending_command(pending, request)
        if operation == "decline":
            return deps.decline_pending_command(pending, request)
        if operation == "retain":
            return deps.retain_pending_command(pending, request)
        if operation == "delete":
            return deps.delete_pending_command(pending, request)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind=f"{operation}_pending_command",
            markdown=f"处理未执行操作失败：{deps.error_detail(exc)}",
        )
    return turn_reply_payload(
        request=request,
        action_kind=f"{operation}_pending_command",
        markdown="未识别的未执行操作处理方式。",
    )


def _spreadsheet_rerun_writeback_decision_payload(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
    sync_requested: bool,
) -> LarkBotReplyPayload:
    action_kind = "sync_writeback_decision" if sync_requested else "skip_writeback_decision"
    try:
        return deps.spreadsheet_rerun_writeback_decision(request, sync_requested)
    except Exception as exc:
        return turn_reply_payload(
            request=request,
            action_kind=action_kind,
            markdown=f"处理表格同步决策失败：{deps.error_detail(exc)}",
        )


def _latest_open_badcase_draft(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> BadcaseDraftView | None:
    for ready_draft in deps.list_ready_drafts():
        if not _same_conversation(draft=ready_draft, request=request):
            continue
        return ready_draft
    draft = (
        deps.latest_draft_for_chat(chat_id=request.chat_id, open_id=request.open_id)
        if request.chat_id
        else None
    )
    if draft is None or draft.status not in {
        "collecting",
        "needs_more_info",
        "ready_for_confirmation",
    }:
        return None
    return draft


def _latest_ready_badcase_draft(
    *,
    request: XiaoDTurnHandleRequest,
    deps: XiaoDHandlerDependencies,
) -> BadcaseDraftView | None:
    for draft in deps.list_ready_drafts():
        if draft.status != "ready_for_confirmation":
            continue
        if not _same_conversation(draft=draft, request=request):
            continue
        if draft.missing_fields:
            continue
        return draft
    return None


def _same_conversation(*, draft: BadcaseDraftView, request: XiaoDTurnHandleRequest) -> bool:
    draft_chat_id = getattr(draft, "chat_id", "")
    draft_open_id = getattr(draft, "open_id", "")
    if draft_chat_id != request.chat_id:
        return False
    return not request.open_id or draft_open_id == request.open_id

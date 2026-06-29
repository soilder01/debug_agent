from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from debug_agent.jobs.service import SubmittedDebugJob
from debug_agent.lark.bot import (
    LarkBotCommandRequest,
    LarkBotCommandResponse,
    LarkBotReplyPayload,
)
from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.storage.repository import (
    LarkBotBadcaseDraft,
    LarkNotificationOutbox,
    LarkBotPendingCommand,
)


class LarkBotPendingCommandCreateRequest(LarkBotCommandRequest):
    ttl_minutes: int = Field(default=30, ge=1, le=1440)
    note: str = ""


class LarkBotPendingCommandConfirmRequest(BaseModel):
    actor: str = ""
    note: str = ""
    require_owner: bool = False


class LarkBotPendingCommandCancelRequest(BaseModel):
    actor: str = ""
    note: str = ""
    require_owner: bool = False


class LarkBotPendingCommandCleanupRequest(BaseModel):
    actor: str = ""
    note: str = ""


class LarkBotPendingCommandListResponse(BaseModel):
    commands: list[LarkBotPendingCommand]
    total_count: int


class LarkBotReplySendRequest(BaseModel):
    actor: str = ""
    dry_run: bool = True
    note: str = ""


class LarkBotReplyDeliveryResponse(BaseModel):
    payload: LarkBotReplyPayload
    connector: LarkConnectorStatus
    sent: bool
    dry_run: bool
    result: dict[str, object] = Field(default_factory=dict)


class LarkBotBadcaseDraftRequest(BaseModel):
    actor: str = ""
    open_id: str = ""
    chat_id: str = ""
    message_id: str = ""
    text: str = Field(default="", max_length=10_000)
    input_source: str = ""
    model_output: str = ""
    expected_output: str = ""
    issue_summary: str = ""
    task_type: str = "generic_json"
    scoring_standard: str = ""
    attachments: list[dict[str, object]] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    resolve_link_content: bool = False


class LarkBotBadcaseDraftListResponse(BaseModel):
    drafts: list[LarkBotBadcaseDraft]
    total_count: int


class LarkBotBadcaseDraftConfirmRequest(BaseModel):
    actor: str = ""
    note: str = ""
    create_job: bool = True


class LarkBotBadcaseDraftConfirmResponse(BaseModel):
    draft: LarkBotBadcaseDraft
    submitted_job: SubmittedDebugJob | None = None


class LarkBotBadcaseDraftCancelRequest(BaseModel):
    actor: str = ""
    note: str = ""


class LarkBotNotificationEnvelope(BaseModel):
    notification_id: str
    kind: Literal["badcase_completion", "badcase_progress", "xiaod_run_progress"]
    draft_id: str = ""
    draft: LarkBotBadcaseDraft | None = None
    payload: LarkBotReplyPayload
    dedupe_key: str
    delivery_state: Literal["pending"] = "pending"
    job_id: str
    case_id: str
    job_status: str
    progress_key: str = ""
    stage: str = ""
    summary: str = ""
    task_panel_key: str = ""
    task_panel_message_id: str = ""
    job_url: str = ""
    report_url: str = ""


class LarkBotNotificationListResponse(BaseModel):
    notifications: list[LarkBotNotificationEnvelope]
    total_count: int


class LarkBotNotificationOutboxListResponse(BaseModel):
    notifications: list[LarkNotificationOutbox]
    total_count: int


class LarkBotNotificationOutboxSentRequest(BaseModel):
    actor: str = ""
    note: str = ""


class LarkBotNotificationOutboxFailedRequest(BaseModel):
    actor: str = ""
    note: str = ""
    error_message: str = Field(default="", max_length=4_000)
    max_attempts: int = Field(default=3, ge=1, le=10)


class LarkBotBadcaseDraftCompletionNotification(LarkBotNotificationEnvelope):
    pass


class LarkBotBadcaseDraftCompletionNotificationListResponse(BaseModel):
    notifications: list[LarkBotBadcaseDraftCompletionNotification]
    total_count: int


class LarkBotBadcaseDraftProgressNotification(LarkBotNotificationEnvelope):
    pass


class LarkBotBadcaseDraftProgressNotificationListResponse(BaseModel):
    notifications: list[LarkBotBadcaseDraftProgressNotification]
    total_count: int


class LarkBotBadcaseDraftProgressNotifiedRequest(BaseModel):
    actor: str = ""
    progress_key: str = Field(default="", max_length=300)
    panel_message_id: str = Field(default="", max_length=120)
    note: str = ""


class LarkBotBadcaseDraftCompletionNotifiedRequest(BaseModel):
    actor: str = ""
    note: str = ""


class LarkBotBadcaseDraftCompletionFailedRequest(BaseModel):
    actor: str = ""
    note: str = ""
    error_message: str = Field(default="", max_length=4_000)
    max_attempts: int = Field(default=3, ge=1, le=10)


def build_lark_bot_router(
    *,
    create_badcase_draft: Callable[[LarkBotBadcaseDraftRequest], LarkBotBadcaseDraft],
    list_badcase_drafts: Callable[[str | None, int, int], LarkBotBadcaseDraftListResponse],
    list_notifications: Callable[[int], LarkBotNotificationListResponse],
    list_notification_outbox: Callable[
        [str | None, int, int], LarkBotNotificationOutboxListResponse
    ],
    mark_notification_outbox_sent: Callable[
        [str, LarkBotNotificationOutboxSentRequest], LarkNotificationOutbox
    ],
    mark_notification_outbox_failed: Callable[
        [str, LarkBotNotificationOutboxFailedRequest], LarkNotificationOutbox
    ],
    list_completion_notifications: Callable[
        [int], LarkBotBadcaseDraftCompletionNotificationListResponse
    ],
    list_progress_notifications: Callable[
        [int], LarkBotBadcaseDraftProgressNotificationListResponse
    ],
    mark_progress_notified: Callable[
        [str, LarkBotBadcaseDraftProgressNotifiedRequest], LarkBotBadcaseDraft
    ],
    get_badcase_draft: Callable[[str], LarkBotBadcaseDraft],
    preview_confirmation_card: Callable[[str], LarkBotReplyPayload],
    preview_confirm_link: Callable[
        [str, Literal["confirm_badcase_draft", "cancel_badcase_draft"], str], Response
    ],
    submit_confirm_link: Callable[
        [str, Literal["confirm_badcase_draft", "cancel_badcase_draft"], str], Response
    ],
    preview_writeback_link: Callable[[str, str], Response],
    submit_writeback_link: Callable[[str, str], Response],
    preview_base_writeback_link: Callable[[str, str], Response],
    submit_base_writeback_link: Callable[[str, str], Response],
    mark_completion_notified: Callable[
        [str, LarkBotBadcaseDraftCompletionNotifiedRequest], LarkBotBadcaseDraft
    ],
    mark_completion_delivery_failed: Callable[
        [str, LarkBotBadcaseDraftCompletionFailedRequest], LarkBotBadcaseDraft
    ],
    cancel_badcase_draft: Callable[[str, LarkBotBadcaseDraftCancelRequest], LarkBotBadcaseDraft],
    confirm_badcase_draft: Callable[
        [str, LarkBotBadcaseDraftConfirmRequest], LarkBotBadcaseDraftConfirmResponse
    ],
    preview_command: Callable[[LarkBotCommandRequest], LarkBotCommandResponse],
    create_pending_command: Callable[[LarkBotPendingCommandCreateRequest], LarkBotPendingCommand],
    list_pending_commands: Callable[[str | None, int, int], LarkBotPendingCommandListResponse],
    get_pending_command: Callable[[str], LarkBotPendingCommand],
    preview_pending_command_reply: Callable[[str], LarkBotReplyPayload],
    send_pending_command_reply: Callable[
        [str, LarkBotReplySendRequest], LarkBotReplyDeliveryResponse
    ],
    confirm_pending_command: Callable[
        [str, LarkBotPendingCommandConfirmRequest], LarkBotPendingCommand
    ],
    cancel_pending_command: Callable[
        [str, LarkBotPendingCommandCancelRequest], LarkBotPendingCommand
    ],
    retain_pending_command: Callable[
        [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
    ],
    delete_pending_command: Callable[
        [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
    ],
    default_delete_pending_command: Callable[
        [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
    ],
    handle_event: Callable[[Request], Awaitable[dict[str, object]]],
) -> APIRouter:
    router = APIRouter()

    @router.post("/lark/bot/badcase-drafts")
    @router.post("/api/lark/bot/badcase-drafts")
    def create_lark_bot_badcase_draft(
        request: LarkBotBadcaseDraftRequest,
    ) -> LarkBotBadcaseDraft:
        return create_badcase_draft(request)

    @router.get("/lark/bot/badcase-drafts")
    @router.get("/api/lark/bot/badcase-drafts")
    def list_lark_bot_badcase_drafts(
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> LarkBotBadcaseDraftListResponse:
        return list_badcase_drafts(status, limit, offset)

    @router.get("/lark/bot/notifications")
    @router.get("/api/lark/bot/notifications")
    def list_lark_bot_notifications(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> LarkBotNotificationListResponse:
        return list_notifications(limit)

    @router.get("/lark/bot/notification-outbox")
    @router.get("/api/lark/bot/notification-outbox")
    def list_lark_bot_notification_outbox(
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> LarkBotNotificationOutboxListResponse:
        return list_notification_outbox(status, limit, offset)

    @router.post("/lark/bot/notification-outbox/{notification_id}/sent")
    @router.post("/api/lark/bot/notification-outbox/{notification_id}/sent")
    def mark_lark_bot_notification_outbox_sent(
        notification_id: str,
        request: LarkBotNotificationOutboxSentRequest,
    ) -> LarkNotificationOutbox:
        return mark_notification_outbox_sent(notification_id, request)

    @router.post("/lark/bot/notification-outbox/{notification_id}/failed")
    @router.post("/api/lark/bot/notification-outbox/{notification_id}/failed")
    def mark_lark_bot_notification_outbox_failed(
        notification_id: str,
        request: LarkBotNotificationOutboxFailedRequest,
    ) -> LarkNotificationOutbox:
        return mark_notification_outbox_failed(notification_id, request)

    @router.get("/lark/bot/badcase-drafts/completion-notifications")
    @router.get("/api/lark/bot/badcase-drafts/completion-notifications")
    def list_lark_bot_badcase_completion_notifications(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> LarkBotBadcaseDraftCompletionNotificationListResponse:
        return list_completion_notifications(limit)

    @router.get("/lark/bot/badcase-drafts/progress-notifications")
    @router.get("/api/lark/bot/badcase-drafts/progress-notifications")
    def list_lark_bot_badcase_progress_notifications(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> LarkBotBadcaseDraftProgressNotificationListResponse:
        return list_progress_notifications(limit)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/progress-notified")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/progress-notified")
    def mark_lark_bot_badcase_progress_notified(
        draft_id: str,
        request: LarkBotBadcaseDraftProgressNotifiedRequest,
    ) -> LarkBotBadcaseDraft:
        return mark_progress_notified(draft_id, request)

    @router.get("/lark/bot/badcase-drafts/{draft_id}")
    @router.get("/api/lark/bot/badcase-drafts/{draft_id}")
    def get_lark_bot_badcase_draft(draft_id: str) -> LarkBotBadcaseDraft:
        return get_badcase_draft(draft_id)

    @router.get("/lark/bot/badcase-drafts/{draft_id}/confirmation-card")
    @router.get("/api/lark/bot/badcase-drafts/{draft_id}/confirmation-card")
    def preview_lark_bot_badcase_confirmation_card(draft_id: str) -> LarkBotReplyPayload:
        return preview_confirmation_card(draft_id)

    @router.get("/lark/bot/badcase-drafts/{draft_id}/confirm-link")
    @router.get("/api/lark/bot/badcase-drafts/{draft_id}/confirm-link")
    def preview_lark_bot_badcase_confirm_link(
        draft_id: str,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"] = Query(
            default="confirm_badcase_draft"
        ),
        token: str = Query(default=""),
    ) -> Response:
        return preview_confirm_link(draft_id, action, token)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/confirm-link")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/confirm-link")
    def submit_lark_bot_badcase_confirm_link(
        draft_id: str,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"] = Query(
            default="confirm_badcase_draft"
        ),
        token: str = Query(default=""),
    ) -> Response:
        return submit_confirm_link(draft_id, action, token)

    @router.get("/lark/bot/badcase-drafts/{draft_id}/writeback-link")
    @router.get("/api/lark/bot/badcase-drafts/{draft_id}/writeback-link")
    def preview_lark_bot_badcase_writeback_link(
        draft_id: str,
        token: str = Query(default=""),
    ) -> Response:
        return preview_writeback_link(draft_id, token)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/writeback-link")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/writeback-link")
    def submit_lark_bot_badcase_writeback_link(
        draft_id: str,
        token: str = Query(default=""),
    ) -> Response:
        return submit_writeback_link(draft_id, token)

    @router.get("/lark/bot/badcase-drafts/{draft_id}/base-writeback-link")
    @router.get("/api/lark/bot/badcase-drafts/{draft_id}/base-writeback-link")
    def preview_lark_bot_badcase_base_writeback_link(
        draft_id: str,
        token: str = Query(default=""),
    ) -> Response:
        return preview_base_writeback_link(draft_id, token)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/base-writeback-link")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/base-writeback-link")
    def submit_lark_bot_badcase_base_writeback_link(
        draft_id: str,
        token: str = Query(default=""),
    ) -> Response:
        return submit_base_writeback_link(draft_id, token)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/completion-notified")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/completion-notified")
    def mark_lark_bot_badcase_completion_notified(
        draft_id: str,
        request: LarkBotBadcaseDraftCompletionNotifiedRequest,
    ) -> LarkBotBadcaseDraft:
        return mark_completion_notified(draft_id, request)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/completion-delivery-failed")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/completion-delivery-failed")
    def mark_lark_bot_badcase_completion_delivery_failed(
        draft_id: str,
        request: LarkBotBadcaseDraftCompletionFailedRequest,
    ) -> LarkBotBadcaseDraft:
        return mark_completion_delivery_failed(draft_id, request)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/cancel")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/cancel")
    def cancel_lark_bot_badcase_draft(
        draft_id: str,
        request: LarkBotBadcaseDraftCancelRequest,
    ) -> LarkBotBadcaseDraft:
        return cancel_badcase_draft(draft_id, request)

    @router.post("/lark/bot/badcase-drafts/{draft_id}/confirm")
    @router.post("/api/lark/bot/badcase-drafts/{draft_id}/confirm")
    def confirm_lark_bot_badcase_draft(
        draft_id: str,
        request: LarkBotBadcaseDraftConfirmRequest,
    ) -> LarkBotBadcaseDraftConfirmResponse:
        return confirm_badcase_draft(draft_id, request)

    @router.post("/lark/bot/commands/preview")
    @router.post("/api/lark/bot/commands/preview")
    def preview_lark_bot_command(request: LarkBotCommandRequest) -> LarkBotCommandResponse:
        return preview_command(request)

    @router.post("/lark/bot/commands/pending")
    @router.post("/api/lark/bot/commands/pending")
    def create_lark_bot_pending_command(
        request: LarkBotPendingCommandCreateRequest,
    ) -> LarkBotPendingCommand:
        return create_pending_command(request)

    @router.get("/lark/bot/commands/pending")
    @router.get("/api/lark/bot/commands/pending")
    def list_lark_bot_pending_commands(
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> LarkBotPendingCommandListResponse:
        return list_pending_commands(status, limit, offset)

    @router.get("/lark/bot/commands/pending/{command_id}")
    @router.get("/api/lark/bot/commands/pending/{command_id}")
    def get_lark_bot_pending_command(command_id: str) -> LarkBotPendingCommand:
        return get_pending_command(command_id)

    @router.get("/lark/bot/commands/pending/{command_id}/reply-preview")
    @router.get("/api/lark/bot/commands/pending/{command_id}/reply-preview")
    def preview_lark_bot_pending_command_reply(command_id: str) -> LarkBotReplyPayload:
        return preview_pending_command_reply(command_id)

    @router.post("/lark/bot/commands/pending/{command_id}/send-reply")
    @router.post("/api/lark/bot/commands/pending/{command_id}/send-reply")
    def send_lark_bot_pending_command_reply(
        command_id: str,
        request: LarkBotReplySendRequest,
    ) -> LarkBotReplyDeliveryResponse:
        return send_pending_command_reply(command_id, request)

    @router.post("/lark/bot/commands/pending/{command_id}/confirm")
    @router.post("/api/lark/bot/commands/pending/{command_id}/confirm")
    def confirm_lark_bot_pending_command(
        command_id: str,
        request: LarkBotPendingCommandConfirmRequest,
    ) -> LarkBotPendingCommand:
        return confirm_pending_command(command_id, request)

    @router.post("/lark/bot/commands/pending/{command_id}/cancel")
    @router.post("/api/lark/bot/commands/pending/{command_id}/cancel")
    def cancel_lark_bot_pending_command(
        command_id: str,
        request: LarkBotPendingCommandCancelRequest,
    ) -> LarkBotPendingCommand:
        return cancel_pending_command(command_id, request)

    @router.post("/lark/bot/commands/pending/{command_id}/retain")
    @router.post("/api/lark/bot/commands/pending/{command_id}/retain")
    def retain_lark_bot_pending_command(
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        return retain_pending_command(command_id, request)

    @router.post("/lark/bot/commands/pending/{command_id}/delete")
    @router.post("/api/lark/bot/commands/pending/{command_id}/delete")
    def delete_lark_bot_pending_command(
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        return delete_pending_command(command_id, request)

    @router.post("/lark/bot/commands/pending/{command_id}/default-delete")
    @router.post("/api/lark/bot/commands/pending/{command_id}/default-delete")
    def default_delete_lark_bot_pending_command(
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        return default_delete_pending_command(command_id, request)

    @router.post("/lark/bot/events")
    @router.post("/api/lark/bot/events")
    async def handle_lark_bot_event(request: Request) -> dict[str, object]:
        return await handle_event(request)

    return router

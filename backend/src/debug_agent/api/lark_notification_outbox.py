from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCompletionNotificationListResponse,
    LarkBotBadcaseDraftProgressNotificationListResponse,
    LarkBotNotificationEnvelope,
    LarkBotNotificationOutboxFailedRequest,
    LarkBotNotificationListResponse,
    LarkBotNotificationOutboxListResponse,
    LarkBotNotificationOutboxSentRequest,
)
from debug_agent.storage.repository import DebugJobRepository, LarkNotificationOutbox


class LarkNotificationOutboxController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        sweep_expired_decisions: Callable[[int], dict[str, int]],
        list_progress_notifications: Callable[
            [int], LarkBotBadcaseDraftProgressNotificationListResponse
        ],
        list_xiaod_run_notifications: Callable[[int], list[LarkBotNotificationEnvelope]],
        list_completion_notifications: Callable[
            [int], LarkBotBadcaseDraftCompletionNotificationListResponse
        ],
        resolved_actor: Callable[[str], str],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
    ) -> None:
        self._job_repository = job_repository
        self._sweep_expired_decisions = sweep_expired_decisions
        self._list_progress_notifications = list_progress_notifications
        self._list_xiaod_run_notifications = list_xiaod_run_notifications
        self._list_completion_notifications = list_completion_notifications
        self._resolved_actor = resolved_actor
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit

    def list_notifications(self, *, limit: int = 20) -> LarkBotNotificationListResponse:
        self.sync(limit=limit)
        notifications = [
            self.envelope_from_outbox(row)
            for row in self._job_repository().list_lark_notification_outbox(
                status="pending", limit=limit
            )
        ]
        return LarkBotNotificationListResponse(
            notifications=notifications,
            total_count=len(notifications),
        )

    def list_outbox(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LarkBotNotificationOutboxListResponse:
        normalized_status = status.strip() if isinstance(status, str) and status.strip() else None
        notifications = self._job_repository().list_lark_notification_outbox(
            status=normalized_status,
            limit=limit,
            offset=offset,
        )
        return LarkBotNotificationOutboxListResponse(
            notifications=notifications,
            total_count=len(notifications),
        )

    def mark_sent(
        self,
        notification_id: str,
        request: LarkBotNotificationOutboxSentRequest,
    ) -> LarkNotificationOutbox:
        updated = self._job_repository().mark_lark_notification_outbox_sent(notification_id)
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail=f"Lark notification outbox item not found: {notification_id}",
            )
        self._save_audit(
            actor=self._resolved_actor(request.actor or "lark-bot-consumer"),
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="notification_outbox_sent",
            context=notification_id,
            risk_action="im_reply",
        )
        return updated

    def mark_failed(
        self,
        notification_id: str,
        request: LarkBotNotificationOutboxFailedRequest,
    ) -> LarkNotificationOutbox:
        existing = self._job_repository().get_lark_notification_outbox(notification_id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Lark notification outbox item not found: {notification_id}",
            )
        error_message = request.error_message or "lark-cli delivery failed"
        next_attempts = int(getattr(existing, "attempts", 0)) + 1
        terminal = next_attempts >= request.max_attempts or is_terminal_delivery_error(
            error_message
        )
        updated = self._job_repository().mark_lark_notification_outbox_failed(
            notification_id,
            last_error=error_message,
            terminal=terminal,
        )
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail=f"Lark notification outbox item not found: {notification_id}",
            )
        self._save_audit(
            actor=self._resolved_actor(request.actor or "lark-bot-consumer"),
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="notification_outbox_failed",
            context=notification_id,
            risk_action="im_reply",
            status="failed" if terminal else "succeeded",
            hint="terminal" if terminal else "retryable",
        )
        return updated

    def sync(self, *, limit: int = 20) -> None:
        self._sweep_expired_decisions(limit)
        progress_response = self._list_progress_notifications(limit)
        for notification in progress_response.notifications:
            self.persist_envelope(notification)
        remaining = max(0, limit - len(progress_response.notifications))
        if remaining <= 0:
            return
        xiaod_notifications = self._list_xiaod_run_notifications(remaining)
        for notification in xiaod_notifications:
            self.persist_envelope(notification)
        remaining = max(0, remaining - len(xiaod_notifications))
        if remaining <= 0:
            return
        completion_response = self._list_completion_notifications(remaining)
        for notification in completion_response.notifications:
            self.persist_envelope(notification)

    def persist_envelope(self, notification: LarkBotNotificationEnvelope) -> None:
        self._job_repository().save_lark_notification_outbox(
            notification_id=notification.notification_id,
            kind=notification.kind,
            dedupe_key=notification.dedupe_key,
            draft_id=notification.draft_id,
            job_id=notification.job_id,
            case_id=notification.case_id,
            job_status=notification.job_status,
            progress_key=notification.progress_key,
            payload=notification.payload.model_dump(mode="json"),
            envelope=notification.model_dump(mode="json"),
        )

    @staticmethod
    def envelope_from_outbox(row: object) -> LarkBotNotificationEnvelope:
        envelope = dict(getattr(row, "envelope"))
        envelope["delivery_state"] = getattr(row, "status")
        return LarkBotNotificationEnvelope.model_validate(envelope)


def is_terminal_delivery_error(error_message: str) -> bool:
    normalized = error_message.lower()
    return any(
        marker in normalized
        for marker in (
            "not a valid {open_message_id}",
            "invalid ids",
            "not exists",
            "message_id",
        )
    )

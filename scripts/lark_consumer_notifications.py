from __future__ import annotations

import sys
import threading
from typing import Any

try:
    from scripts.lark_consumer_payloads import string_value
except ModuleNotFoundError:
    from lark_consumer_payloads import string_value


def get_json(url: str) -> dict[str, Any]:
    raise RuntimeError("consumer notification get_json dependency is not bound")


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("consumer notification post_json dependency is not bound")


def run_lark_delivery_args(
    *, args: list[str], profile: str, identity: str, lark_cli: str
) -> bool | dict[str, Any]:
    raise RuntimeError("consumer notification delivery dependency is not bound")


_SENT_PROGRESS_KEYS: set[str] = set()


def poll_completion_notifications(
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
    interval_seconds: float,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        deliver_notifications(
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
            fallback_to_legacy=True,
        )
        stop_event.wait(max(interval_seconds, 1))


def deliver_notifications(
    *,
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
    fallback_to_legacy: bool = False,
) -> int:
    try:
        response = get_json(
            f"{base_url.rstrip('/')}/api/lark/bot/notifications?limit=20"
        )
    except RuntimeError as exc:
        print(
            f"[consumer] notification list failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        if fallback_to_legacy:
            return deliver_progress_notifications(
                base_url=base_url,
                profile=profile,
                identity=identity,
                lark_cli=lark_cli,
            ) + deliver_completion_notifications(
                base_url=base_url,
                profile=profile,
                identity=identity,
                lark_cli=lark_cli,
            )
        return 0
    notifications = response.get("notifications")
    if not isinstance(notifications, list):
        return 0
    delivered_count = 0
    for notification in notifications:
        if not isinstance(notification, dict):
            continue
        kind = string_value(notification.get("kind"))
        if kind == "badcase_progress":
            if deliver_progress_notification(
                notification=notification,
                base_url=base_url,
                profile=profile,
                identity=identity,
                lark_cli=lark_cli,
            ):
                delivered_count += 1
            continue
        if kind == "badcase_completion" and deliver_completion_notification(
            notification=notification,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        ):
            delivered_count += 1
            continue
        if kind and deliver_outbox_notification(
            notification=notification,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        ):
            delivered_count += 1
    return delivered_count


def deliver_outbox_notification(
    *,
    notification: dict[str, object],
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> bool:
    notification_id = string_value(notification.get("notification_id"))
    args = notification_delivery_args(notification)
    if not notification_id or not args:
        return False
    delivery_result = run_lark_delivery_args(
        args=args,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    )
    if not delivery_result:
        mark_notification_outbox_failed(
            base_url=base_url,
            notification_id=notification_id,
            args=args,
        )
        return False
    mark_notification_outbox_sent(
        base_url=base_url,
        notification_id=notification_id,
    )
    return True


def mark_notification_outbox_sent(*, base_url: str, notification_id: str) -> None:
    try:
        post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/notification-outbox/{notification_id}/sent",
            {"actor": "lark-bot-consumer", "note": "Notification outbox item sent."},
        )
    except RuntimeError as exc:
        print(
            f"[consumer] notification outbox mark failed: {exc}",
            file=sys.stderr,
            flush=True,
        )


def mark_notification_outbox_failed(
    *,
    base_url: str,
    notification_id: str,
    args: list[str],
) -> None:
    try:
        post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/notification-outbox/{notification_id}/failed",
            {
                "actor": "lark-bot-consumer",
                "note": f"Notification outbox delivery failed for {delivery_target_label(args)}.",
                "error_message": "lark-cli delivery failed; see consumer stderr for details.",
                "max_attempts": 3,
            },
        )
    except RuntimeError as exc:
        print(
            f"[consumer] notification outbox failure mark failed: {exc}",
            file=sys.stderr,
            flush=True,
        )


def deliver_progress_notifications(
    *,
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> int:
    try:
        response = get_json(
            f"{base_url.rstrip('/')}/api/lark/bot/badcase-drafts/progress-notifications?limit=20"
        )
    except RuntimeError as exc:
        print(
            f"[consumer] progress notification list failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 0
    notifications = response.get("notifications")
    if not isinstance(notifications, list):
        return 0
    delivered_count = 0
    for notification in notifications:
        if not isinstance(notification, dict):
            continue
        if deliver_progress_notification(
            notification=notification,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        ):
            delivered_count += 1
    return delivered_count


def deliver_progress_notification(
    *,
    notification: dict[str, object],
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> bool:
    progress_key = string_value(notification.get("progress_key"))
    draft_id = notification_draft_id(notification)
    if not draft_id and ":" in progress_key:
        draft_id = progress_key.split(":", 1)[0]
    args = notification_delivery_args(notification)
    if (
        not progress_key
        or not draft_id
        or progress_key in _SENT_PROGRESS_KEYS
        or not args
    ):
        return False
    delivery_result = run_lark_delivery_args(
        args=args,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    )
    used_fallback = False
    if not delivery_result:
        fallback_args = notification_fallback_delivery_args(notification)
        if not fallback_args:
            return False
        delivery_result = run_lark_delivery_args(
            args=fallback_args,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        )
        if not delivery_result:
            return False
        used_fallback = True
    mark_progress_notification_sent(
        base_url=base_url,
        draft_id=draft_id,
        progress_key=progress_key,
        panel_message_id=progress_panel_message_id(
            notification,
            delivery_result,
            prefer_delivery_result=used_fallback,
        ),
    )
    _SENT_PROGRESS_KEYS.add(progress_key)
    return True


def mark_progress_notification_sent(
    *,
    base_url: str,
    draft_id: str,
    progress_key: str,
    panel_message_id: str = "",
) -> None:
    payload = {
        "actor": "lark-bot-consumer",
        "progress_key": progress_key,
        "note": "Progress notification sent.",
    }
    if panel_message_id:
        payload["panel_message_id"] = panel_message_id
    try:
        post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/badcase-drafts/{draft_id}/progress-notified",
            payload,
        )
    except RuntimeError as exc:
        print(
            f"[consumer] progress notification mark failed: {exc}",
            file=sys.stderr,
            flush=True,
        )


def progress_panel_message_id(
    notification: dict[str, object],
    delivery_result: object,
    *,
    prefer_delivery_result: bool = False,
) -> str:
    if not isinstance(delivery_result, dict):
        existing_panel_message_id = string_value(
            notification.get("task_panel_message_id")
        )
        return "" if prefer_delivery_result else existing_panel_message_id
    delivered_message_id = string_value(delivery_result.get("message_id"))
    if prefer_delivery_result and delivered_message_id:
        return delivered_message_id
    existing_panel_message_id = string_value(notification.get("task_panel_message_id"))
    if existing_panel_message_id:
        return existing_panel_message_id
    return delivered_message_id


def notification_fallback_delivery_args(notification: dict[str, object]) -> list[str]:
    payload = (
        notification.get("payload")
        if isinstance(notification.get("payload"), dict)
        else {}
    )
    fallback_args = payload.get("fallback_delivery_args")
    if not isinstance(fallback_args, list):
        return []
    return [item for item in fallback_args if isinstance(item, str) and item]


def deliver_completion_notifications(
    *,
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> int:
    try:
        response = get_json(
            f"{base_url.rstrip('/')}/api/lark/bot/badcase-drafts/completion-notifications?limit=20"
        )
    except RuntimeError as exc:
        print(
            f"[consumer] completion notification list failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 0
    notifications = response.get("notifications")
    if not isinstance(notifications, list):
        return 0
    delivered_count = 0
    for notification in notifications:
        if not isinstance(notification, dict):
            continue
        if deliver_completion_notification(
            notification=notification,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        ):
            delivered_count += 1
    return delivered_count


def deliver_completion_notification(
    *,
    notification: dict[str, object],
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> bool:
    draft_id = notification_draft_id(notification)
    args = notification_delivery_args(notification)
    if not draft_id or not args:
        return False
    if not run_lark_delivery_args(
        args=args,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    ):
        mark_completion_notification_failed(
            base_url=base_url,
            draft_id=draft_id,
            args=args,
        )
        return False
    try:
        post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/badcase-drafts/{draft_id}/completion-notified",
            {"actor": "lark-bot-consumer", "note": "Completion notification sent."},
        )
    except RuntimeError as exc:
        print(
            f"[consumer] completion notification mark failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return False
    return True


def notification_draft_id(notification: dict[str, object]) -> str:
    draft_id = string_value(notification.get("draft_id"))
    if draft_id:
        return draft_id
    draft = (
        notification.get("draft") if isinstance(notification.get("draft"), dict) else {}
    )
    return string_value(draft.get("draft_id"))


def notification_delivery_args(notification: dict[str, object]) -> list[str]:
    payload = (
        notification.get("payload")
        if isinstance(notification.get("payload"), dict)
        else {}
    )
    delivery_args = payload.get("delivery_args")
    if not isinstance(delivery_args, list):
        return []
    return [item for item in delivery_args if isinstance(item, str) and item]


def mark_completion_notification_failed(
    *,
    base_url: str,
    draft_id: str,
    args: list[str],
) -> None:
    try:
        post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/badcase-drafts/{draft_id}/completion-delivery-failed",
            {
                "actor": "lark-bot-consumer",
                "note": f"Completion notification delivery failed for {delivery_target_label(args)}.",
                "error_message": "lark-cli delivery failed; see consumer stderr for details.",
                "max_attempts": 3,
            },
        )
    except RuntimeError as exc:
        print(
            f"[consumer] completion notification failure mark failed: {exc}",
            file=sys.stderr,
            flush=True,
        )


def delivery_target_label(args: list[str]) -> str:
    for flag in ("--message-id", "--chat-id", "--user-id"):
        if flag in args:
            index = args.index(flag)
            if index + 1 < len(args):
                return f"{flag} {args[index + 1]}"
    return "unknown target"

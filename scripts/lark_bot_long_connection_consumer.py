from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_SRC = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if BACKEND_SRC.exists() and str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from debug_agent.lark.xiaod_orchestrator import strip_bot_mention_prefix  # noqa: E402

try:
    from scripts.lark_consumer_payloads import (
        attachments_from_lark_message_content,
        card_action_actor,
        card_action_value,
        compact_lark_attachment,
        deduplicate_attachments,
        event_attachments,
        event_dict_string,
        event_string,
        event_text,
        is_addressed_to_bot,
        is_card_action_event,
        lark_event_type,
        object_string,
        object_to_plain_dict,
        should_process_event,
        string_value,
        text_from_lark_message_content,
    )
except ModuleNotFoundError:
    from lark_consumer_payloads import (
        attachments_from_lark_message_content,
        card_action_actor,
        card_action_value,
        compact_lark_attachment,
        deduplicate_attachments,
        event_attachments,
        event_dict_string,
        event_string,
        event_text,
        is_addressed_to_bot,
        is_card_action_event,
        lark_event_type,
        object_string,
        object_to_plain_dict,
        should_process_event,
        string_value,
        text_from_lark_message_content,
    )

try:
    from scripts import lark_consumer_notifications as _consumer_notifications
except ModuleNotFoundError:
    import lark_consumer_notifications as _consumer_notifications

try:
    from scripts.lark_consumer_utils import (
        env_value,
        lark_idempotency_key,
        lark_text,
        load_env_file,
        parse_delivery_result,
        project_root,
        resolve_executable,
        sdk_card_action_event_to_payload,
        sdk_message_event_to_flat_event,
        stop_process,
    )
except ModuleNotFoundError:
    from lark_consumer_utils import (
        env_value,
        lark_idempotency_key,
        lark_text,
        load_env_file,
        parse_delivery_result,
        project_root,
        resolve_executable,
        sdk_card_action_event_to_payload,
        sdk_message_event_to_flat_event,
        stop_process,
    )

try:
    from scripts.lark_consumer_cli import (
        build_consume_command,
        parse_args,
        stream_stderr,
    )
except ModuleNotFoundError:
    from lark_consumer_cli import (
        build_consume_command,
        parse_args,
        stream_stderr,
    )

__all__ = [
    "attachments_from_lark_message_content",
    "card_action_actor",
    "card_action_value",
    "compact_lark_attachment",
    "deduplicate_attachments",
    "event_attachments",
    "event_dict_string",
    "event_string",
    "event_text",
    "is_addressed_to_bot",
    "is_card_action_event",
    "lark_event_type",
    "object_string",
    "object_to_plain_dict",
    "should_process_event",
    "string_value",
    "text_from_lark_message_content",
]


def _bind_notification_dependencies() -> None:
    _consumer_notifications.get_json = get_json
    _consumer_notifications.post_json = post_json
    _consumer_notifications.run_lark_delivery_args = run_lark_delivery_args
    _consumer_notifications._SENT_PROGRESS_KEYS = _SENT_PROGRESS_KEYS


def poll_completion_notifications(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.poll_completion_notifications(*args, **kwargs)


def deliver_notifications(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_notifications(*args, **kwargs)


def deliver_outbox_notification(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_outbox_notification(*args, **kwargs)


def mark_notification_outbox_sent(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.mark_notification_outbox_sent(*args, **kwargs)


def mark_notification_outbox_failed(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.mark_notification_outbox_failed(*args, **kwargs)


def deliver_progress_notifications(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_progress_notifications(*args, **kwargs)


def deliver_progress_notification(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_progress_notification(*args, **kwargs)


def mark_progress_notification_sent(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.mark_progress_notification_sent(*args, **kwargs)


def progress_panel_message_id(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.progress_panel_message_id(*args, **kwargs)


def notification_fallback_delivery_args(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.notification_fallback_delivery_args(*args, **kwargs)


def deliver_completion_notifications(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_completion_notifications(*args, **kwargs)


def deliver_completion_notification(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.deliver_completion_notification(*args, **kwargs)


def notification_draft_id(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.notification_draft_id(*args, **kwargs)


def notification_delivery_args(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.notification_delivery_args(*args, **kwargs)


def mark_completion_notification_failed(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.mark_completion_notification_failed(*args, **kwargs)


def delivery_target_label(*args: Any, **kwargs: Any):
    _bind_notification_dependencies()
    return _consumer_notifications.delivery_target_label(*args, **kwargs)


EVENT_KEY = "im.message.receive_v1"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
BACKEND_TURN_HANDLE_ENABLED = True
EVENT_DEDUP_TTL_SECONDS = 600
PERSISTED_EVENT_DEDUP_TTL_SECONDS = 14 * 24 * 60 * 60
_SEEN_EVENT_KEYS: dict[str, float] = {}
_PERSISTENT_EVENT_DEDUP_ENABLED = False
_PERSISTENT_EVENT_KEYS: dict[str, float] | None = None
_PERSISTENT_EVENT_STORE_PATH: Path | None = None
_SENT_PROGRESS_KEYS: set[str] = set()
BOT_MENTION_PREFIXES = (
    "@小d",
    "@debug-agent",
    "@debug_agent",
    "@debug agent",
    "@xiaod",
    "@xiao d",
)
BOT_MENTION_NAMES = (
    "小d",
    "debug-agent",
    "debug_agent",
    "debug agent",
    "xiaod",
    "xiao d",
)


def main() -> int:
    load_env_file(project_root() / ".env")
    args = parse_args()
    profile = args.profile or os.environ.get("LARK_CLI_PROFILE", "")
    identity = args.identity or os.environ.get("LARK_CLI_IDENTITY", "bot")
    base_url = args.base_url or os.environ.get(
        "DEBUG_AGENT_REPORT_BASE_URL", DEFAULT_BASE_URL
    )
    if args.transport == "sdk":
        return run_sdk_consumer(
            args=args,
            base_url=base_url,
            profile=profile,
            identity=identity,
        )
    return run_lark_cli_consumer(
        args=args,
        base_url=base_url,
        profile=profile,
        identity=identity,
    )


def run_lark_cli_consumer(
    *,
    args: argparse.Namespace,
    base_url: str,
    profile: str,
    identity: str,
) -> int:
    configure_persistent_event_dedup(args.seen_events_path)
    command = build_consume_command(args=args, profile=profile, identity=identity)

    print(
        f"[consumer] starting event_key={args.event_key} profile={profile or 'default'} "
        f"identity={identity} transport=lark-cli backend={base_url.rstrip('/')}",
        file=sys.stderr,
        flush=True,
    )
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    ready = threading.Event()
    stderr_thread = threading.Thread(
        target=stream_stderr,
        args=(process, ready, args.event_key),
        daemon=True,
    )
    stderr_thread.start()
    if not ready.wait(args.ready_timeout_seconds):
        process.terminate()
        print(
            f"[consumer] lark-cli did not become ready within {args.ready_timeout_seconds}s",
            file=sys.stderr,
            flush=True,
        )
        return 1
    stop_event = threading.Event()
    completion_thread: threading.Thread | None = None
    if not args.no_send_replies and args.completion_poll_seconds > 0:
        completion_thread = threading.Thread(
            target=poll_completion_notifications,
            args=(
                base_url,
                profile,
                identity,
                args.lark_cli,
                args.completion_poll_seconds,
                stop_event,
            ),
            daemon=True,
        )
        completion_thread.start()
    assert process.stdout is not None
    try:
        for line in process.stdout:
            handle_event_line(
                line=line,
                base_url=base_url,
                profile=profile,
                identity=identity,
                send_replies=not args.no_send_replies,
                lark_cli=args.lark_cli,
            )
    except KeyboardInterrupt:
        print("[consumer] interrupted, stopping...", file=sys.stderr, flush=True)
    finally:
        stop_event.set()
        if completion_thread is not None:
            completion_thread.join(timeout=5)
        stop_process(process)
    return process.wait(timeout=10) if process.poll() is not None else 0


def run_sdk_consumer(
    *,
    args: argparse.Namespace,
    base_url: str,
    profile: str,
    identity: str,
) -> int:
    configure_persistent_event_dedup(args.seen_events_path)
    app_id = args.app_id or env_value("LARK_APP_ID", "FEISHU_APP_ID", "App_ID")
    app_secret = args.app_secret or env_value(
        "LARK_APP_SECRET",
        "FEISHU_APP_SECRET",
        "App_Secret",
    )
    if not app_id or not app_secret:
        print(
            "[consumer] sdk transport requires app id and app secret "
            "(LARK_APP_ID/LARK_APP_SECRET or App_ID/App_Secret).",
            file=sys.stderr,
            flush=True,
        )
        return 1
    verification_token = args.verification_token or env_value(
        "LARK_BOT_VERIFICATION_TOKEN", allow_commented=True
    )
    encrypt_key = args.encrypt_key or env_value(
        "LARK_BOT_ENCRYPT_KEY", allow_commented=True
    )
    try:
        import lark_oapi as lark
        from lark_oapi import ws
        from lark_oapi.event.callback.model.p2_card_action_trigger import (
            P2CardActionTriggerResponse,
        )
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
    except ImportError as exc:
        print(
            f"[consumer] sdk transport requires lark_oapi: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    stop_event = threading.Event()
    completion_thread: threading.Thread | None = None
    if not args.no_send_replies and args.completion_poll_seconds > 0:
        completion_thread = threading.Thread(
            target=poll_completion_notifications,
            args=(
                base_url,
                profile,
                identity,
                args.lark_cli,
                args.completion_poll_seconds,
                stop_event,
            ),
            daemon=True,
        )
        completion_thread.start()

    def on_message(data: Any) -> None:
        handle_sdk_message_event(
            data=data,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=args.lark_cli,
            send_replies=not args.no_send_replies,
        )

    def on_card_action(data: Any) -> Any:
        response = handle_sdk_card_action_event(
            data=data,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=args.lark_cli,
            send_replies=not args.no_send_replies,
        )
        toast = response.get("toast") if isinstance(response.get("toast"), dict) else {}
        if not toast:
            toast = {
                "type": "success" if response.get("handled") else "info",
                "content": "小D已收到卡片操作。",
            }
        return P2CardActionTriggerResponse({"toast": toast})

    dispatcher = (
        EventDispatcherHandler.builder(
            encrypt_key,
            verification_token,
            lark.LogLevel.INFO,
        )
        .register_p2_im_message_receive_v1(on_message)
        .register_p2_card_action_trigger(on_card_action)
        .build()
    )
    print(
        f"[consumer] starting event_key=im.message.receive_v1,card.action.trigger "
        f"profile={profile or 'default'} identity={identity} transport=sdk "
        f"backend={base_url.rstrip('/')}",
        file=sys.stderr,
        flush=True,
    )
    client = ws.Client(
        app_id,
        app_secret,
        log_level=lark.LogLevel.INFO,
        event_handler=dispatcher,
    )
    try:
        client.start()
    except KeyboardInterrupt:
        print(
            "[consumer] interrupted, stopping sdk consumer...",
            file=sys.stderr,
            flush=True,
        )
    finally:
        stop_event.set()
        if completion_thread is not None:
            completion_thread.join(timeout=5)
    return 0


def handle_sdk_message_event(
    *,
    data: Any,
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
    send_replies: bool = True,
) -> threading.Thread:
    event = sdk_message_event_to_flat_event(data)
    thread = threading.Thread(
        target=handle_event_line,
        kwargs={
            "line": json.dumps(event, ensure_ascii=False),
            "base_url": base_url,
            "profile": profile,
            "identity": identity,
            "send_replies": send_replies,
            "lark_cli": lark_cli,
        },
        daemon=True,
    )
    thread.start()
    return thread


def handle_event_line(
    *,
    line: str,
    base_url: str,
    profile: str,
    identity: str,
    send_replies: bool,
    lark_cli: str,
) -> None:
    stripped = line.strip()
    if not stripped:
        return
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        print(
            f"[consumer] skip invalid json line: {stripped[:200]}",
            file=sys.stderr,
            flush=True,
        )
        return
    if not isinstance(event, dict):
        print("[consumer] skip non-object event", file=sys.stderr, flush=True)
        return
    if is_duplicate_event(event):
        print(
            f"[consumer] ignored duplicate event key={event_dedup_key(event)}",
            file=sys.stderr,
            flush=True,
        )
        return
    if is_card_action_event(event):
        handle_card_action_event(
            event=event,
            base_url=base_url,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
            send_replies=send_replies,
        )
        mark_event_processed(event)
        return
    text = event_text(event)
    if not should_process_event(event=event, text=text):
        print("[consumer] ignored non-command message", file=sys.stderr, flush=True)
        return
    action_text = strip_bot_mention_prefix(text)
    if not send_replies:
        mark_event_processed(event)
        return
    if handle_xiaod_turn_with_backend(
        event=event,
        text=action_text,
        base_url=base_url,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    ):
        mark_event_processed(event)
        return
    reply_backend_unavailable(
        event=event,
        base_url=base_url,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    )
    mark_event_processed(event)


def is_duplicate_event(event: dict[str, Any]) -> bool:
    key = event_dedup_key(event)
    if not key:
        return False
    now = time.monotonic()
    prune_seen_event_keys(now)
    first_seen_at = _SEEN_EVENT_KEYS.get(key)
    if first_seen_at is not None and now - first_seen_at < EVENT_DEDUP_TTL_SECONDS:
        return True
    if is_persisted_duplicate_event(key):
        _SEEN_EVENT_KEYS[key] = now
        return True
    _SEEN_EVENT_KEYS[key] = now
    return False


def event_dedup_key(event: dict[str, Any]) -> str:
    event_type = lark_event_type(event) or "unknown"
    if is_card_action_event(event):
        value = card_action_value(event)
        action = event_dict_string(value, "action")
        draft_id = event_dict_string(value, "draft_id")
        command_id = event_dict_string(value, "command_id")
        actor = card_action_actor(event)
        if action or draft_id or command_id or actor:
            return f"{event_type}:card:{action}:{draft_id}:{command_id}:{actor}"
    message_id = event_string(event, "message_id") or event_string(event, "id")
    if message_id:
        return f"{event_type}:message:{message_id}"
    event_id = event_string(event, "event_id") or event_string(event, "uuid")
    header = event.get("header")
    if not event_id and isinstance(header, dict):
        event_id = event_dict_string(header, "event_id")
    if event_id:
        return f"{event_type}:event:{event_id}"
    return ""


def prune_seen_event_keys(now: float) -> None:
    expired = [
        key
        for key, first_seen_at in _SEEN_EVENT_KEYS.items()
        if now - first_seen_at >= EVENT_DEDUP_TTL_SECONDS
    ]
    for key in expired:
        _SEEN_EVENT_KEYS.pop(key, None)


def configure_persistent_event_dedup(path: str = "") -> None:
    global \
        _PERSISTENT_EVENT_DEDUP_ENABLED, \
        _PERSISTENT_EVENT_KEYS, \
        _PERSISTENT_EVENT_STORE_PATH
    normalized = path.strip()
    if normalized.lower() in {"off", "none", "disabled", "false", "0"}:
        _PERSISTENT_EVENT_DEDUP_ENABLED = False
        _PERSISTENT_EVENT_KEYS = {}
        _PERSISTENT_EVENT_STORE_PATH = None
        return
    _PERSISTENT_EVENT_DEDUP_ENABLED = True
    _PERSISTENT_EVENT_KEYS = None
    _PERSISTENT_EVENT_STORE_PATH = (
        Path(normalized)
        if normalized
        else project_root() / ".tmp" / "lark-bot-consumer-seen-events.jsonl"
    )


def is_persisted_duplicate_event(key: str) -> bool:
    if not _PERSISTENT_EVENT_DEDUP_ENABLED:
        return False
    return key in persisted_event_keys()


def mark_event_processed(event: dict[str, Any]) -> None:
    key = event_dedup_key(event)
    if not key or not _PERSISTENT_EVENT_DEDUP_ENABLED:
        return
    keys = persisted_event_keys()
    if key in keys:
        return
    seen_at = time.time()
    keys[key] = seen_at
    path = persistent_event_store_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"key": key, "seen_at": seen_at}, ensure_ascii=False) + "\n"
        )


def persisted_event_keys() -> dict[str, float]:
    global _PERSISTENT_EVENT_KEYS
    if _PERSISTENT_EVENT_KEYS is None:
        _PERSISTENT_EVENT_KEYS = load_persisted_event_keys()
    return _PERSISTENT_EVENT_KEYS


def load_persisted_event_keys() -> dict[str, float]:
    path = persistent_event_store_path()
    if path is None or not path.exists():
        return {}
    now = time.time()
    keys: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        key = string_value(record.get("key"))
        seen_at = float(record.get("seen_at") or 0)
        if key and now - seen_at < PERSISTED_EVENT_DEDUP_TTL_SECONDS:
            keys[key] = seen_at
    return keys


def persistent_event_store_path() -> Path | None:
    return _PERSISTENT_EVENT_STORE_PATH


def handle_card_action_event(
    *,
    event: dict[str, Any],
    base_url: str,
    profile: str = "",
    identity: str = "bot",
    lark_cli: str = "lark-cli",
    send_replies: bool = True,
) -> dict[str, Any]:
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/lark/bot/events", event)
    except RuntimeError as exc:
        print(
            f"[consumer] card action post failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return {"handled": False, "error": str(exc)}
    print(
        "[consumer] card_action "
        f"handled={response.get('handled')} action={response.get('action', '')}",
        file=sys.stderr,
        flush=True,
    )
    if send_replies:
        deliver_backend_reply(
            response=response,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
            label="card action follow-up",
        )
    return response


def handle_sdk_card_action_event(
    *,
    data: Any,
    base_url: str,
    profile: str = "",
    identity: str = "bot",
    lark_cli: str = "lark-cli",
    send_replies: bool = True,
) -> dict[str, Any]:
    return handle_card_action_event(
        event=sdk_card_action_event_to_payload(data),
        base_url=base_url,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
        send_replies=send_replies,
    )


def handle_xiaod_turn_with_backend(
    *,
    event: dict[str, Any],
    text: str,
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> bool:
    if not BACKEND_TURN_HANDLE_ENABLED:
        return False
    try:
        response = post_json(
            f"{base_url.rstrip('/')}/api/lark/bot/xiaod/turns/handle",
            xiaod_turn_handle_payload(
                event=event,
                text=text,
                profile=profile,
                identity=identity,
            ),
        )
    except RuntimeError as exc:
        print(
            f"[consumer] backend xiaod turn handle failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return False
    if not response.get("handled"):
        return False
    if deliver_backend_reply(
        response=response,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
        label="xiaod turn reply",
    ):
        return True
    reply = response.get("reply")
    markdown = string_value(reply.get("markdown")) if isinstance(reply, dict) else ""
    if markdown:
        reply_markdown_to_event(
            event=event,
            markdown=markdown,
            profile=profile,
            identity=identity,
            lark_cli=lark_cli,
        )
    return True


def deliver_backend_reply(
    *,
    response: dict[str, Any],
    profile: str,
    identity: str,
    lark_cli: str,
    label: str,
) -> bool:
    reply = response.get("reply")
    if not isinstance(reply, dict):
        return False
    delivery_args = reply.get("delivery_args")
    if not isinstance(delivery_args, list):
        return False
    args = [item for item in delivery_args if isinstance(item, str) and item]
    if not args:
        return False
    delivered = run_lark_delivery_args(
        args=args,
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    )
    if delivered:
        print(f"[consumer] {label} sent", file=sys.stderr, flush=True)
    return bool(delivered)


def xiaod_turn_handle_payload(
    *,
    event: dict[str, Any],
    text: str,
    profile: str,
    identity: str,
) -> dict[str, object]:
    attachments = event_attachments(event)
    return {
        "text": text,
        "has_attachments": bool(attachments),
        "actor": event_string(event, "sender_id"),
        "open_id": event_string(event, "sender_id"),
        "chat_id": event_string(event, "chat_id"),
        "message_id": event_string(event, "message_id") or event_string(event, "id"),
        "tenant_key": event_string(event, "tenant_key"),
        "identity": identity or "bot",
        "profile": profile,
        "attachments": attachments,
        "resolve_link_content": True,
    }


def reply_backend_unavailable(
    *,
    event: dict[str, Any],
    base_url: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> None:
    reply_markdown_to_event(
        event=event,
        markdown=(
            "小D已经收到消息，但 Debug Agent 后端暂时不可用或未返回可处理结果。\n\n"
            f"后端地址：{base_url.rstrip('/')}\n"
            "我不会在长连接脚本里另跑一套业务逻辑。请先恢复后端后重试。"
        ),
        profile=profile,
        identity=identity,
        lark_cli=lark_cli,
    )


def send_reply(
    *,
    lark_cli: str,
    profile: str,
    identity: str,
    message_id: str,
    markdown: str,
) -> None:
    text = lark_text(markdown)
    command = [resolve_executable(lark_cli)]
    if profile:
        command.extend(["--profile", profile])
    command.extend(
        [
            "im",
            "+messages-reply",
            "--message-id",
            message_id,
            "--text",
            text,
            "--idempotency-key",
            lark_idempotency_key(),
            "--as",
            identity or "bot",
        ]
    )
    print(
        f"[consumer] sending reply message_id={message_id} mode=text chars={len(text)}",
        file=sys.stderr,
        flush=True,
    )
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(
            "[consumer] reply send failed "
            f"message_id={message_id} stderr={result.stderr.strip()}",
            file=sys.stderr,
            flush=True,
        )
        return
    print(f"[consumer] reply sent message_id={message_id}", file=sys.stderr, flush=True)


def run_lark_delivery_args(
    *,
    args: list[str],
    profile: str,
    identity: str,
    lark_cli: str,
) -> bool | dict[str, Any]:
    command = [resolve_executable(lark_cli)]
    if profile:
        command.extend(["--profile", profile])
    command.extend(args)
    if "--as" not in args:
        command.extend(["--as", identity or "bot"])
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(
            f"[consumer] completion notification send failed: {result.stderr.strip()}",
            file=sys.stderr,
            flush=True,
        )
        return False
    print("[consumer] completion notification sent", file=sys.stderr, flush=True)
    parsed = parse_delivery_result(result.stdout)
    return parsed if parsed else True


def reply_markdown_to_event(
    *,
    event: dict[str, Any],
    markdown: str,
    profile: str,
    identity: str,
    lark_cli: str,
) -> None:
    message_id = event_string(event, "message_id") or event_string(event, "id")
    if not message_id:
        print(
            "[consumer] cannot reply: message_id missing",
            file=sys.stderr,
            flush=True,
        )
        return
    send_reply(
        lark_cli=lark_cli,
        profile=profile,
        identity=identity,
        message_id=message_id,
        markdown=markdown,
    )


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return request_json(request)


def get_json(url: str) -> dict[str, Any]:
    return request_json(urllib_request.Request(url, method="GET"))


def request_json(request: urllib_request.Request) -> dict[str, Any]:
    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {detail}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    except TimeoutError as exc:
        raise RuntimeError(f"request timed out: {request.full_url}") from exc
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc
    try:
        data = json.loads(body or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("response is not valid JSON") from exc
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())

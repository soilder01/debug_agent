from __future__ import annotations

import json
import os
from typing import Any

from debug_agent.lark.xiaod_orchestrator import (
    has_command_prefix,
    normalized_text,
)


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


def is_card_action_event(event: dict[str, Any]) -> bool:
    event_type = lark_event_type(event)
    return "card" in event_type and "action" in event_type


def lark_event_type(event: dict[str, Any]) -> str:
    header = event.get("header")
    if isinstance(header, dict):
        event_type = header.get("event_type")
        if isinstance(event_type, str) and event_type.strip():
            return event_type.strip()
    for key in ("event_type", "type"):
        event_type = event.get(key)
        if isinstance(event_type, str) and event_type.strip():
            return event_type.strip()
    return ""


def card_action_value(event: dict[str, Any]) -> dict[str, Any]:
    raw_event = event.get("event")
    event_dict = raw_event if isinstance(raw_event, dict) else event
    for key in ("action", "action_value", "value"):
        raw = event_dict.get(key)
        if isinstance(raw, dict):
            value = raw.get("value")
            return value if isinstance(value, dict) else raw
    return {}


def card_action_actor(event: dict[str, Any]) -> str:
    raw_event = event.get("event")
    event_dict = raw_event if isinstance(raw_event, dict) else event
    operator = event_dict.get("operator")
    if isinstance(operator, dict):
        return (
            event_dict_string(operator, "open_id")
            or event_dict_string(operator, "user_id")
            or event_dict_string(operator, "union_id")
        )
    return ""


def event_text(event: dict[str, Any]) -> str:
    content = event.get("content")
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return ""
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
        if isinstance(parsed, dict):
            return text_from_lark_message_content(parsed) or stripped
        return stripped
    return string_value(event.get("text"))


def event_attachments(event: dict[str, Any]) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    raw_attachments = event.get("attachments")
    if isinstance(raw_attachments, list):
        attachments.extend(item for item in raw_attachments if isinstance(item, dict))
    content = event.get("content")
    if isinstance(content, str) and content.strip():
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        attachments.extend(attachments_from_lark_message_content(parsed))
    return deduplicate_attachments(attachments)


def attachments_from_lark_message_content(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        current = compact_lark_attachment(value)
        attachments = [current] if current else []
        content = value.get("content")
        if isinstance(content, list):
            attachments.extend(attachments_from_lark_message_content(content))
        return attachments
    if isinstance(value, list):
        attachments: list[dict[str, Any]] = []
        for item in value:
            attachments.extend(attachments_from_lark_message_content(item))
        return attachments
    return []


def compact_lark_attachment(value: dict[str, Any]) -> dict[str, Any] | None:
    tag = string_value(value.get("tag")) or string_value(value.get("type"))
    attachment_tags = {"img", "image", "file", "media", "video", "audio"}
    keys = ("file_key", "image_key", "key", "file_name", "name", "mime_type")
    has_attachment_key = any(string_value(value.get(key)) for key in keys)
    if tag not in attachment_tags and not has_attachment_key:
        return None
    attachment: dict[str, Any] = {}
    if tag:
        attachment["type"] = tag
    for key in keys:
        item = string_value(value.get(key))
        if item:
            attachment[key] = item
    if tag in attachment_tags:
        for key in ("href", "url"):
            item = string_value(value.get(key))
            if item:
                attachment[key] = item
    size = value.get("size")
    if isinstance(size, (int, float)):
        attachment["size"] = size
    return attachment or None


def deduplicate_attachments(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for attachment in attachments:
        marker = json.dumps(attachment, sort_keys=True, ensure_ascii=False)
        if marker in seen:
            continue
        seen.add(marker)
        deduplicated.append(attachment)
    return deduplicated


def text_from_lark_message_content(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        tag = string_value(value.get("tag")) or string_value(value.get("type"))
        if tag == "at":
            mention = (
                string_value(value.get("text"))
                or string_value(value.get("user_name"))
                or string_value(value.get("name"))
            )
            if mention:
                return mention if mention.startswith("@") else f"@{mention}"
        direct = string_value(value.get("text")) or string_value(value.get("content"))
        if direct:
            return direct
        href = string_value(value.get("href"))
        if href:
            return href
        content = value.get("content")
        if isinstance(content, list):
            return text_from_lark_message_content(content)
        return ""
    if isinstance(value, list):
        parts = [text_from_lark_message_content(item) for item in value]
        non_empty = [part for part in parts if part]
        if not non_empty:
            return ""
        if any(isinstance(item, list) for item in value):
            return "\n".join(non_empty)
        return "".join(non_empty)
    return ""


def should_process_event(*, event: dict[str, Any], text: str) -> bool:
    normalized = normalized_text(text)
    if not normalized:
        return bool(event_attachments(event))
    if has_command_prefix(normalized):
        return True
    chat_type = event_string(event, "chat_type").lower()
    if chat_type == "p2p":
        return True
    if is_addressed_to_bot(event=event, text=text):
        return True
    return False


def is_addressed_to_bot(*, event: dict[str, Any], text: str) -> bool:
    normalized = normalized_text(text)
    if any(normalized.startswith(prefix) for prefix in BOT_MENTION_PREFIXES):
        return True
    bot_open_id = os.environ.get("LARK_BOT_OPEN_ID", "").strip()
    mentions = event.get("mentions")
    if not isinstance(mentions, list):
        return False
    for mention in mentions:
        if not isinstance(mention, dict):
            continue
        mention_id = (
            event_dict_string(mention, "open_id")
            or event_dict_string(mention, "user_id")
            or event_dict_string(mention, "id")
        )
        if bot_open_id and mention_id == bot_open_id:
            return True
        mention_name = normalized_text(
            event_dict_string(mention, "name")
            or event_dict_string(mention, "user_name")
            or event_dict_string(mention, "display_name")
        )
        if mention_name in BOT_MENTION_NAMES:
            return True
    return False


def event_string(event: dict[str, Any], key: str) -> str:
    return string_value(event.get(key))


def event_dict_string(event: dict[str, Any], key: str) -> str:
    return string_value(event.get(key))


def object_string(value: Any, key: str) -> str:
    if isinstance(value, dict):
        return string_value(value.get(key))
    return string_value(getattr(value, key, ""))


def string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def object_to_plain_dict(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): object_to_plain_dict(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [object_to_plain_dict(item) for item in value if item is not None]
    raw = getattr(value, "__dict__", None)
    if isinstance(raw, dict):
        return {
            key: object_to_plain_dict(item)
            for key, item in raw.items()
            if not key.startswith("_") and item is not None
        }
    return str(value)

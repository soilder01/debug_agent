from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from scripts.lark_consumer_payloads import (
        object_string,
        object_to_plain_dict,
        string_value,
    )
except ModuleNotFoundError:
    from lark_consumer_payloads import object_string, object_to_plain_dict, string_value


EVENT_KEY = "im.message.receive_v1"


def sdk_card_action_event_to_payload(data: Any) -> dict[str, Any]:
    payload = object_to_plain_dict(data)
    if not isinstance(payload, dict):
        payload = {}
    header = payload.get("header")
    if not isinstance(header, dict):
        header = {}
        payload["header"] = header
    header.setdefault("event_type", "card.action.trigger")
    payload.setdefault("schema", "2.0")
    return payload


def sdk_message_event_to_flat_event(data: Any) -> dict[str, Any]:
    header = getattr(data, "header", None)
    event = getattr(data, "event", None)
    message = getattr(event, "message", None)
    sender = getattr(event, "sender", None)
    sender_id = getattr(sender, "sender_id", None)
    event_type = object_string(header, "event_type") or EVENT_KEY
    message_id = object_string(message, "message_id")
    return {
        "type": event_type,
        "event_type": event_type,
        "event_id": object_string(header, "event_id"),
        "tenant_key": object_string(header, "tenant_key")
        or object_string(event, "tenant_key"),
        "timestamp": object_string(header, "create_time"),
        "message_id": message_id,
        "id": message_id,
        "chat_id": object_string(message, "chat_id"),
        "chat_type": object_string(message, "chat_type"),
        "message_type": object_string(message, "message_type"),
        "content": object_string(message, "content"),
        "create_time": object_string(message, "create_time"),
        "sender_id": (
            object_string(sender_id, "open_id")
            or object_string(sender_id, "user_id")
            or object_string(sender_id, "union_id")
        ),
        "mentions": object_to_plain_dict(getattr(message, "mentions", [])),
    }


def lark_idempotency_key() -> str:
    return f"da-{uuid4().hex[:24]}"


def lark_text(value: str) -> str:
    cleaned = "".join(_lark_text_char(char) for char in value)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()
    return cleaned or "我暂时没有组织出可发送的回复。"


def _lark_text_char(char: str) -> str:
    code = ord(char)
    if char in {"\n", "\t"}:
        return char
    if code < 32 or 0x7F <= code <= 0x9F:
        return ""
    return char


def parse_delivery_result(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {}
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    data = parsed.get("data")
    if isinstance(data, dict):
        message_id = string_value(data.get("message_id"))
        chat_id = string_value(data.get("chat_id"))
        result: dict[str, Any] = {}
        if message_id:
            result["message_id"] = message_id
        if chat_id:
            result["chat_id"] = chat_id
        if result:
            return result
    message_id = string_value(parsed.get("message_id"))
    chat_id = string_value(parsed.get("chat_id"))
    result = {}
    if message_id:
        result["message_id"] = message_id
    if chat_id:
        result["chat_id"] = chat_id
    return result


def resolve_executable(name: str) -> str:
    return shutil.which(name) or name


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if process.stdin is not None:
        try:
            process.stdin.close()
        except OSError:
            pass
    deadline = time.monotonic() + 5
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        process.terminate()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in os.environ:
            continue
        os.environ[normalized_key] = value.strip().strip('"').strip("'")


def env_value(*keys: str, allow_commented: bool = False) -> str:
    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    if not allow_commented:
        return ""
    env_path = project_root() / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            stripped = stripped[1:].strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in keys and value.strip():
            return value.strip().strip('"').strip("'")
    return ""


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

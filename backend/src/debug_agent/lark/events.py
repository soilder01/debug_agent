from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from hmac import compare_digest

from Crypto.Cipher import AES

from debug_agent.lark.schemas import LarkBotCommandRequest, LarkBotEventParseResult

def validate_lark_bot_event_token(payload: dict[str, object], expected_token: str) -> bool:
    if not expected_token:
        return True
    token = lark_bot_event_token(payload)
    return bool(token) and compare_digest(token, expected_token)


def lark_bot_event_token(payload: dict[str, object]) -> str:
    header = _dict(payload.get("header"))
    return _string(payload.get("token")) or _string(header.get("token"))


def calculate_lark_bot_event_signature(
    *,
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    body: bytes,
) -> str:
    prefix = f"{timestamp}{nonce}{encrypt_key}".encode("utf-8")
    return hashlib.sha256(prefix + body).hexdigest()


def validate_lark_bot_event_signature(
    *,
    headers: Mapping[str, str],
    body: bytes,
    encrypt_key: str,
) -> bool:
    if not encrypt_key:
        return True
    timestamp = _header_value(headers, "x-lark-request-timestamp")
    nonce = _header_value(headers, "x-lark-request-nonce")
    signature = _header_value(headers, "x-lark-signature")
    if not timestamp or not nonce or not signature:
        return False
    expected = calculate_lark_bot_event_signature(
        timestamp=timestamp,
        nonce=nonce,
        encrypt_key=encrypt_key,
        body=body,
    )
    return compare_digest(signature, expected)


def decrypt_lark_bot_event_payload(
    payload: dict[str, object], encrypt_key: str
) -> dict[str, object]:
    encrypted = _string(payload.get("encrypt"))
    if not encrypted:
        return payload
    try:
        encrypted_bytes = base64.b64decode(encrypted)
    except Exception as exc:
        raise ValueError("Lark bot encrypted payload is not valid base64.") from exc
    if len(encrypted_bytes) <= AES.block_size or len(encrypted_bytes) % AES.block_size != 0:
        raise ValueError("Lark bot encrypted payload has invalid block size.")
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = encrypted_bytes[: AES.block_size]
    encrypted_event = encrypted_bytes[AES.block_size :]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = cipher.decrypt(encrypted_event)
    unpadded = _pkcs7_unpad(padded)
    try:
        decrypted = json.loads(unpadded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Lark bot encrypted payload decrypted to invalid JSON.") from exc
    if not isinstance(decrypted, dict):
        raise ValueError("Lark bot encrypted payload must decrypt to a JSON object.")
    return decrypted


def parse_lark_bot_event_payload(payload: dict[str, object]) -> LarkBotEventParseResult:
    challenge = _string(payload.get("challenge"))
    if challenge:
        return LarkBotEventParseResult(event_type="url_verification", challenge=challenge)

    header = _dict(payload.get("header"))
    event = _dict(payload.get("event"))
    event_type = _string(header.get("event_type")) or _string(payload.get("event_type"))
    if not event_type and event:
        event_type = "im.message.receive_v1"
    if event_type != "im.message.receive_v1":
        return LarkBotEventParseResult(
            event_type=event_type or "unknown",
            ignored_reason="unsupported_event_type",
        )

    message = _dict(event.get("message"))
    sender = _dict(event.get("sender"))
    text = _message_text(message)
    if not text:
        return LarkBotEventParseResult(
            event_type=event_type, ignored_reason="empty_or_non_text_message"
        )
    command_request = LarkBotCommandRequest(
        text=text,
        actor=_sender_open_id(sender),
        open_id=_sender_open_id(sender),
        chat_id=_string(message.get("chat_id")) or _string(event.get("chat_id")),
        message_id=_string(message.get("message_id")),
        tenant_key=_string(header.get("tenant_key")) or _string(payload.get("tenant_key")),
        identity="bot",
    )
    return LarkBotEventParseResult(event_type=event_type, command_request=command_request)


def _pkcs7_unpad(value: bytes) -> bytes:
    if not value:
        raise ValueError("Lark bot encrypted payload is empty after decrypt.")
    padding_size = value[-1]
    if padding_size < 1 or padding_size > AES.block_size:
        raise ValueError("Lark bot encrypted payload has invalid padding.")
    padding = value[-padding_size:]
    if padding != bytes([padding_size]) * padding_size:
        raise ValueError("Lark bot encrypted payload has invalid padding.")
    return value[:-padding_size]


def _message_text(message: dict[str, object]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return ""
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
        if isinstance(parsed, dict):
            return _string(parsed.get("text")) or _string(parsed.get("content"))
        return stripped
    return _string(message.get("text"))


def _sender_open_id(sender: dict[str, object]) -> str:
    sender_id = _dict(sender.get("sender_id"))
    return (
        _string(sender_id.get("open_id"))
        or _string(sender_id.get("user_id"))
        or _string(sender.get("open_id"))
        or _string(sender.get("sender_id"))
    )


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _header_value(headers: Mapping[str, str], name: str) -> str:
    direct = headers.get(name) or headers.get(name.title())
    if direct:
        return direct.strip()
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value.strip()
    return ""

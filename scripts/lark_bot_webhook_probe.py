from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from Crypto.Cipher import AES


def endpoint_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/lark/bot/events"


def build_url_verification_payload(*, challenge: str, token: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "type": "url_verification",
        "challenge": challenge,
    }
    if token:
        payload["token"] = token
    return payload


def build_message_event_payload(
    *,
    text: str,
    token: str,
    open_id: str,
    chat_id: str,
    message_id: str,
    tenant_key: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
            "tenant_key": tenant_key,
        },
        "event": {
            "sender": {"sender_id": {"open_id": open_id}},
            "message": {
                "message_id": message_id,
                "chat_id": chat_id,
                "message_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        },
    }
    if token:
        payload["token"] = token
    return payload


def request_body_and_headers(
    payload: dict[str, object],
    *,
    encrypt_key: str,
    encrypt_payload: bool,
    timestamp: str,
    nonce: str,
) -> tuple[bytes, dict[str, str]]:
    if encrypt_payload:
        if not encrypt_key:
            raise ValueError("--encrypt requires --encrypt-key.")
        encrypted = encrypt_lark_payload(payload, encrypt_key)
        body = json.dumps({"encrypt": encrypted}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    else:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if encrypt_key:
        headers["X-Lark-Request-Timestamp"] = timestamp
        headers["X-Lark-Request-Nonce"] = nonce
        headers["X-Lark-Signature"] = calculate_lark_signature(
            timestamp=timestamp,
            nonce=nonce,
            encrypt_key=encrypt_key,
            body=body,
        )
    return body, headers


def calculate_lark_signature(*, timestamp: str, nonce: str, encrypt_key: str, body: bytes) -> str:
    return hashlib.sha256(f"{timestamp}{nonce}{encrypt_key}".encode("utf-8") + body).hexdigest()


def encrypt_lark_payload(payload: dict[str, object], encrypt_key: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    padding_size = AES.block_size - (len(raw) % AES.block_size)
    padded = raw + bytes([padding_size]) * padding_size
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = b"debug-agent-iv01"
    encrypted = AES.new(key, AES.MODE_CBC, iv).encrypt(padded)
    return base64.b64encode(iv + encrypted).decode("ascii")


def post_probe(
    *,
    base_url: str,
    payload: dict[str, object],
    encrypt_key: str,
    encrypt_payload: bool,
    timeout_seconds: float,
    timestamp: str,
    nonce: str,
) -> dict[str, Any]:
    body, headers = request_body_and_headers(
        payload,
        encrypt_key=encrypt_key,
        encrypt_payload=encrypt_payload,
        timestamp=timestamp,
        nonce=nonce,
    )
    url = endpoint_url(base_url)
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "url": url,
                "request": _request_summary(body=body, headers=headers, encrypt_payload=encrypt_payload),
                "response": _json_or_text(response_body),
                "error": "",
            }
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status_code": exc.code,
            "url": url,
            "request": _request_summary(body=body, headers=headers, encrypt_payload=encrypt_payload),
            "response": _json_or_text(response_body),
            "error": response_body,
        }
    except (OSError, URLError) as exc:
        return {
            "ok": False,
            "status_code": 0,
            "url": url,
            "request": _request_summary(body=body, headers=headers, encrypt_payload=encrypt_payload),
            "response": {},
            "error": str(exc),
        }


def build_probe_report(
    *,
    mode: str,
    base_url: str,
    result: dict[str, Any],
    expected_challenge: str,
) -> dict[str, Any]:
    checks = [
        _check(
            key="http_status",
            label="HTTP 响应",
            passed=bool(result.get("ok")),
            detail=f"status_code={result.get('status_code', 0)}",
            action="确认 Debug Agent 后端已启动，且回调地址可从当前网络访问。",
        )
    ]
    response = result.get("response", {})
    if mode == "url-verification":
        challenge = response.get("challenge") if isinstance(response, dict) else ""
        checks.append(
            _check(
                key="challenge",
                label="URL Verification",
                passed=challenge == expected_challenge,
                detail=f"challenge={challenge}",
                action="检查 Verification Token、Encrypt Key、签名和回调路径配置。",
            )
        )
    if mode == "message":
        handled = bool(response.get("handled")) if isinstance(response, dict) else False
        checks.append(
            _check(
                key="message_handled",
                label="消息事件处理",
                passed=handled,
                detail=f"handled={handled}",
                action="检查事件类型、消息内容和 bot command 解析。",
            )
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": mode,
        "base_url": base_url.rstrip("/"),
        "status": _overall_status(checks),
        "checks": checks,
        "result": result,
    }


def _request_summary(*, body: bytes, headers: dict[str, str], encrypt_payload: bool) -> dict[str, Any]:
    safe_headers = {key: value for key, value in headers.items() if key.lower() != "x-lark-signature"}
    return {
        "body_size_bytes": len(body),
        "encrypted": encrypt_payload,
        "signed": "X-Lark-Signature" in headers,
        "headers": safe_headers,
    }


def _json_or_text(value: str) -> object:
    try:
        return json.loads(value) if value else {}
    except json.JSONDecodeError:
        return value


def _check(*, key: str, label: str, passed: bool, detail: str, action: str) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "status": "passed" if passed else "failed",
        "detail": detail,
        "action": "无需处理。" if passed else action,
    }


def _overall_status(checks: list[dict[str, str]]) -> str:
    return "failed" if any(check["status"] == "failed" for check in checks) else "passed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Debug Agent's Feishu bot webhook endpoint.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--mode", choices=["url-verification", "message"], default="url-verification")
    parser.add_argument("--token", default="")
    parser.add_argument("--encrypt-key", default="")
    parser.add_argument("--encrypt", action="store_true")
    parser.add_argument("--challenge", default="debug-agent-url-verification")
    parser.add_argument("--text", default="/debug status")
    parser.add_argument("--open-id", default="ou_debug_probe")
    parser.add_argument("--chat-id", default="oc_debug_probe")
    parser.add_argument("--message-id", default="om_debug_probe")
    parser.add_argument("--tenant-key", default="tenant-debug-probe")
    parser.add_argument("--timestamp", default="1700000000")
    parser.add_argument("--nonce", default="debug-agent-probe")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args(argv)

    payload = (
        build_url_verification_payload(challenge=args.challenge, token=args.token)
        if args.mode == "url-verification"
        else build_message_event_payload(
            text=args.text,
            token=args.token,
            open_id=args.open_id,
            chat_id=args.chat_id,
            message_id=args.message_id,
            tenant_key=args.tenant_key,
        )
    )
    result = post_probe(
        base_url=args.base_url,
        payload=payload,
        encrypt_key=args.encrypt_key,
        encrypt_payload=args.encrypt,
        timeout_seconds=args.timeout_seconds,
        timestamp=args.timestamp,
        nonce=args.nonce,
    )
    report = build_probe_report(
        mode=args.mode,
        base_url=args.base_url,
        result=result,
        expected_challenge=args.challenge,
    )
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

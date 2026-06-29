from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal

from fastapi import HTTPException, Request

from debug_agent.lark.bot import (
    LarkBotCommandResponse,
    LarkBotEventResponse,
    decrypt_lark_bot_event_payload,
    parse_lark_bot_event_payload,
    validate_lark_bot_event_signature,
    validate_lark_bot_event_token,
)


class LarkBotEventController:
    def __init__(
        self,
        *,
        event_mode: Callable[[], Literal["webhook", "long_connection"]],
        verification_token: Callable[[], str],
        encrypt_key: Callable[[], str],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
        handle_card_action_event: Callable[[dict[str, object]], dict[str, object] | None],
        preview_command: Callable[[object], LarkBotCommandResponse],
    ) -> None:
        self._event_mode = event_mode
        self._verification_token = verification_token
        self._encrypt_key = encrypt_key
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit
        self._handle_card_action_event = handle_card_action_event
        self._preview_command = preview_command

    async def handle_event(self, request: Request) -> dict[str, object]:
        payload = await self.payload_from_request(request)
        if self._event_mode() == "webhook" and not validate_lark_bot_event_token(
            payload, self._verification_token()
        ):
            self._save_audit(
                actor="",
                identity="bot",
                profile=self._lark_cli_profile(),
                operation="event_rejected",
                status="failed",
                context="lark_bot_event",
                risk_action="webhook_security",
                error_type="invalid_verification_token",
                hint="检查 LARK_BOT_VERIFICATION_TOKEN 与飞书事件订阅中的 Verification Token 是否一致。",
            )
            raise HTTPException(status_code=403, detail="Invalid Lark bot verification token.")
        card_action_response = self._handle_card_action_event(payload)
        if card_action_response is not None:
            return card_action_response
        parsed = parse_lark_bot_event_payload(payload)
        if parsed.challenge:
            return {"challenge": parsed.challenge}
        if parsed.command_request is None:
            return LarkBotEventResponse(
                event_type=parsed.event_type,
                handled=False,
                ignored_reason=parsed.ignored_reason,
            ).model_dump(mode="json")
        return LarkBotEventResponse(
            event_type=parsed.event_type,
            handled=True,
            command=self._preview_command(parsed.command_request),
        ).model_dump(mode="json")

    async def payload_from_request(self, request: Request) -> dict[str, object]:
        body = await request.body()
        try:
            payload = json.loads(body.decode("utf-8") if body else "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid Lark bot event JSON.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400, detail="Lark bot event payload must be a JSON object."
            )
        has_encrypted_payload = isinstance(payload.get("encrypt"), str) and bool(
            payload.get("encrypt")
        )
        if self._event_mode() == "long_connection" and not has_encrypted_payload:
            return payload
        encrypt_key = self._encrypt_key()
        if not encrypt_key:
            return payload
        if self._event_mode() == "webhook" and not validate_lark_bot_event_signature(
            headers=request.headers, body=body, encrypt_key=encrypt_key
        ):
            self._save_audit(
                actor="",
                identity="bot",
                profile=self._lark_cli_profile(),
                operation="event_rejected",
                status="failed",
                context="lark_bot_event",
                risk_action="webhook_security",
                error_type="invalid_signature",
                hint="检查 LARK_BOT_ENCRYPT_KEY 和 X-Lark-Signature、Timestamp、Nonce 是否来自飞书事件回调。",
            )
            raise HTTPException(status_code=403, detail="Invalid Lark bot event signature.")
        try:
            return decrypt_lark_bot_event_payload(payload, encrypt_key)
        except ValueError as exc:
            self._save_audit(
                actor="",
                identity="bot",
                profile=self._lark_cli_profile(),
                operation="event_rejected",
                status="failed",
                context="lark_bot_event",
                risk_action="webhook_security",
                error_type="decrypt_failed",
                hint=str(exc),
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

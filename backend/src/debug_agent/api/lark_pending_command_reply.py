from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from debug_agent.api.lark_bot_routes import LarkBotReplyDeliveryResponse, LarkBotReplySendRequest
from debug_agent.lark.bot import LarkBotReplyPayload, build_lark_bot_pending_command_reply
from debug_agent.lark.connector import LarkCliConnector, LarkCliError
from debug_agent.storage.repository import DebugJobRepository


class LarkPendingCommandReplyController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        resolved_actor: Callable[[str], str],
        im_connector: Callable[[str, str, str], LarkCliConnector],
        save_audit: Callable[..., None],
    ) -> None:
        self._job_repository = job_repository
        self._resolved_actor = resolved_actor
        self._im_connector = im_connector
        self._save_audit = save_audit

    def preview(self, command_id: str) -> LarkBotReplyPayload:
        command = self._pending_command(command_id)
        return build_lark_bot_pending_command_reply(
            command,
            identity=command.identity,
            dry_run=True,
        )

    def send(
        self,
        command_id: str,
        request: LarkBotReplySendRequest,
    ) -> LarkBotReplyDeliveryResponse:
        command = self._pending_command(command_id)
        actor = self._resolved_actor(request.actor or command.actor or command.open_id)
        connector = self._im_connector(actor, command.identity, command.profile)
        payload = build_lark_bot_pending_command_reply(
            command,
            identity=connector.status().identity,
            dry_run=request.dry_run,
        )
        if not payload.delivery_args:
            raise HTTPException(
                status_code=400,
                detail="Lark bot reply target is missing. Provide message_id, chat_id, or open_id.",
            )
        if request.dry_run:
            self._save_audit(
                actor=actor,
                identity=command.identity,
                profile=command.profile,
                operation="reply_send_dry_run",
                context=command.command_text,
                risk_action="im_reply",
            )
            return LarkBotReplyDeliveryResponse(
                payload=payload,
                connector=connector.status(),
                sent=False,
                dry_run=True,
            )
        try:
            result = connector.run_json(payload.delivery_args)
        except LarkCliError as exc:
            self._save_audit(
                actor=actor,
                identity=command.identity,
                profile=command.profile,
                operation="reply_send_failed",
                status="failed",
                context=command.command_text,
                risk_action="im_reply",
                error_type=exc.error_type,
                hint=exc.hint,
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        self._save_audit(
            actor=actor,
            identity=command.identity,
            profile=command.profile,
            operation="reply_sent",
            context=command.command_text,
            risk_action="im_reply",
        )
        return LarkBotReplyDeliveryResponse(
            payload=payload,
            connector=connector.status(),
            sent=True,
            dry_run=False,
            result=result,
        )

    def _pending_command(self, command_id: str):
        command = self._job_repository().get_lark_bot_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        return command

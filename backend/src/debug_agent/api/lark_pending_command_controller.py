from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.badcase_intake_parsers import _object_string_list
from debug_agent.api.lark_bot_routes import (
    LarkBotPendingCommandCreateRequest,
    LarkBotPendingCommandListResponse,
)
from debug_agent.artifacts.layout import safe_path_fragment
from debug_agent.lark.bot import (
    LarkBotCommandResponse,
    LarkBotReplyPayload,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand


class LarkPendingCommandController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        preview_command: Callable[[object], LarkBotCommandResponse],
        resolved_actor: Callable[[str], str],
        save_audit: Callable[..., None],
        attach_spreadsheet_rerun_preflight: Callable[[object], None],
        action_bool: Callable[[dict[str, object], str], bool],
        spreadsheet_rerun_preflight_from_action: Callable[[dict[str, object]], dict[str, object]],
        execute_pending_command: Callable[[LarkBotPendingCommand], dict[str, object]],
        fail_background: Callable[..., None],
        http_exception_detail_text: Callable[[object], str],
    ) -> None:
        self._job_repository = job_repository
        self._preview_command = preview_command
        self._resolved_actor = resolved_actor
        self._save_audit = save_audit
        self._attach_spreadsheet_rerun_preflight = attach_spreadsheet_rerun_preflight
        self._action_bool = action_bool
        self._spreadsheet_rerun_preflight_from_action = spreadsheet_rerun_preflight_from_action
        self._execute_pending_command = execute_pending_command
        self._fail_background = fail_background
        self._http_exception_detail_text = http_exception_detail_text

    def create(self, request: LarkBotPendingCommandCreateRequest) -> LarkBotPendingCommand:
        preview = self._preview_command(request)
        if not preview.action.confirmation_required:
            raise HTTPException(
                status_code=400,
                detail="Only write-risk bot commands require pending confirmation.",
            )
        return self.create_from_preview(
            preview=preview,
            note=request.note,
            ttl_minutes=request.ttl_minutes,
        )

    def create_from_preview(
        self,
        *,
        preview: LarkBotCommandResponse,
        note: str,
        ttl_minutes: int = 30,
    ) -> LarkBotPendingCommand:
        self._attach_spreadsheet_rerun_preflight(preview.action)
        command = self._job_repository().create_lark_bot_pending_command(
            command_id=str(uuid4()),
            actor=preview.audit.actor,
            open_id=preview.audit.open_id,
            chat_id=preview.audit.chat_id,
            message_id=preview.audit.message_id,
            tenant_key=preview.audit.tenant_key,
            identity=preview.audit.identity,
            profile=preview.audit.profile,
            command_text=preview.audit.safe_command,
            action_kind=preview.action.kind,
            action=preview.action.model_dump(mode="json"),
            card=preview.card.model_dump(mode="json"),
            note=note,
            expires_at=(datetime.now(UTC) + timedelta(minutes=ttl_minutes)).isoformat(
                timespec="seconds"
            ),
        )
        self._save_audit(
            actor=command.actor,
            identity=command.identity,
            profile=command.profile,
            operation="pending_command_created",
            context=command.command_text,
            risk_action="confirmation_required",
        )
        return command

    def list_commands(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LarkBotPendingCommandListResponse:
        normalized_status = status.strip() if isinstance(status, str) and status.strip() else None
        repository = self._job_repository()
        return LarkBotPendingCommandListResponse(
            commands=repository.list_lark_bot_pending_commands(
                status=normalized_status,
                limit=limit,
                offset=offset,
            ),
            total_count=repository.count_lark_bot_pending_commands(status=normalized_status),
        )

    def get(self, command_id: str) -> LarkBotPendingCommand:
        command = self._job_repository().get_lark_bot_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        return command

    def ensure_spreadsheet_rerun_active_run(self, command: LarkBotPendingCommand) -> object:
        existing = self.active_spreadsheet_rerun_run_for_command(command)
        if existing is not None:
            return existing
        report_requested = self._action_bool(command.action, "auto_closure") or self._action_bool(
            command.action, "report"
        )
        writeback_requested = self._action_bool(command.action, "writeback")
        return self._job_repository().create_xiaod_execution_run(
            run_id=str(uuid4()),
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            command_id=command.command_id,
            action_kind=command.action_kind,
            status="active",
            summary={
                "command_id": command.command_id,
                "message_id": command.message_id,
                "chat_id": command.chat_id,
                "open_id": command.open_id,
                "preflight": self._spreadsheet_rerun_preflight_from_action(command.action),
                "report_requested": report_requested,
                "writeback_requested": writeback_requested,
                "writeback_decision_status": "not_ready"
                if writeback_requested
                else "not_requested",
                "stage": "starting",
            },
        )

    def mark_spreadsheet_rerun_batch_started(
        self,
        *,
        command: LarkBotPendingCommand,
        batch_id: str,
    ) -> None:
        run = self.active_spreadsheet_rerun_run_for_command(command)
        if run is None:
            return
        summary = dict(getattr(run, "summary", {}) or {})
        summary.update(
            {
                "batch_id": batch_id,
                "job_ids": _object_string_list(summary, "job_ids"),
                "stage": "batch_started",
            }
        )
        self._job_repository().complete_xiaod_execution_run(
            str(getattr(run, "run_id", "")),
            status="active",
            summary=summary,
        )

    @staticmethod
    def spreadsheet_rerun_batch_id(sheet_id: str) -> str:
        safe_sheet_id = safe_path_fragment(sheet_id)
        digest = hashlib.sha1(safe_sheet_id.encode("utf-8")).hexdigest()[:8]
        return f"sheet-rerun-{digest}-{uuid4().hex[:12]}"

    def start_background(self, command_id: str, *, actor: str) -> None:
        def runner() -> None:
            command = self._job_repository().get_lark_bot_pending_command(command_id)
            if (
                command is None
                or command.status != "confirmed"
                or command.action_kind != "spreadsheet_rerun"
            ):
                return
            try:
                execution_result = self._execute_pending_command(command)
            except FileNotFoundError as exc:
                self._fail_background(
                    command=command,
                    actor=actor,
                    error_message=str(exc),
                    error_type="not_found",
                )
                return
            except HTTPException as exc:
                self._fail_background(
                    command=command,
                    actor=actor,
                    error_message=self._http_exception_detail_text(exc.detail),
                    error_type="http_error",
                )
                return
            except Exception as exc:  # noqa: BLE001
                self._fail_background(
                    command=command,
                    actor=actor,
                    error_message=str(exc)[:500],
                    error_type=type(exc).__name__,
                )
                return
            completed = self._job_repository().complete_lark_bot_pending_command(
                command.command_id,
                status="executed",
                execution_result=execution_result,
            )
            if completed is None:
                return
            self._save_audit(
                actor=actor,
                identity=command.identity,
                profile=command.profile,
                operation="pending_command_executed",
                context=command.command_text,
                risk_action=command.action_kind,
            )

        thread = threading.Thread(
            target=runner,
            name=f"lark-pending-command-{command_id[:8]}",
            daemon=True,
        )
        thread.start()

    def active_spreadsheet_rerun_run_for_command(
        self,
        command: LarkBotPendingCommand,
    ) -> object | None:
        for run in self._job_repository().list_xiaod_execution_runs(active_only=True, limit=500):
            if (
                getattr(run, "command_id", "") == command.command_id
                and getattr(run, "tenant_key", "") == command.tenant_key
                and getattr(run, "chat_id", "") == command.chat_id
                and getattr(run, "open_id", "") == command.open_id
                and getattr(run, "action_kind", "") == command.action_kind
            ):
                return run
        return None

    def create_cleanup_decision(self, command: LarkBotPendingCommand) -> None:
        repository = self._job_repository()
        decision = repository.get_pending_xiaod_decision(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="retain_or_delete_unexecuted_command",
        )
        if decision is not None:
            return
        repository.create_xiaod_pending_decision(
            decision_id=str(uuid4()),
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="retain_or_delete_unexecuted_command",
            command_id=command.command_id,
            payload={"action_kind": command.action_kind, "command_text": command.command_text},
            note="User declined continuation; waiting for retain/delete.",
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds"),
        )

    def action_reply(
        self,
        *,
        command: LarkBotPendingCommand,
        action_kind: str,
        markdown: str,
        content: dict[str, object] | None = None,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"card-action-{command.command_id}-{uuid4()}",
            action_kind=action_kind,
            status=command.status,
            target_type=self.reply_target_type(command),
            message_id=command.message_id,
            chat_id=command.chat_id,
            user_id=command.open_id,
            markdown=markdown,
            message_type="interactive" if content else "post",
            content=content or {},
            idempotency_key=lark_bot_idempotency_key("pending"),
        )
        return payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(payload, identity="bot", dry_run=False)
            }
        )

    @staticmethod
    def reply_target_type(
        command: LarkBotPendingCommand,
    ) -> Literal["message", "chat", "user", "none"]:
        if command.message_id:
            return "message"
        if command.chat_id:
            return "chat"
        if command.open_id:
            return "user"
        return "none"

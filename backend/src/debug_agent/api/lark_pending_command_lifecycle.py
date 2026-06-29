from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from debug_agent.api.lark_bot_routes import (
    LarkBotPendingCommandCancelRequest,
    LarkBotPendingCommandCleanupRequest,
    LarkBotPendingCommandConfirmRequest,
)
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand


class LarkPendingCommandLifecycleController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        resolved_actor: Callable[[str], str],
        pending_command_expired: Callable[[LarkBotPendingCommand], bool],
        ensure_spreadsheet_rerun_active_run: Callable[[LarkBotPendingCommand], object],
        start_pending_command_background: Callable[[str, str], None],
        execute_pending_command: Callable[[LarkBotPendingCommand], dict[str, object]],
        save_audit: Callable[..., None],
        http_exception_detail_text: Callable[[object], str],
        active_spreadsheet_rerun_run_for_command: Callable[[LarkBotPendingCommand], object | None],
    ) -> None:
        self._job_repository = job_repository
        self._resolved_actor = resolved_actor
        self._pending_command_expired = pending_command_expired
        self._ensure_spreadsheet_rerun_active_run = ensure_spreadsheet_rerun_active_run
        self._start_pending_command_background = start_pending_command_background
        self._execute_pending_command = execute_pending_command
        self._save_audit = save_audit
        self._http_exception_detail_text = http_exception_detail_text
        self._active_spreadsheet_rerun_run_for_command = active_spreadsheet_rerun_run_for_command

    def confirm(
        self,
        command_id: str,
        request: LarkBotPendingCommandConfirmRequest,
    ) -> LarkBotPendingCommand:
        repository = self._job_repository()
        command = repository.get_lark_bot_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        if command.status != "pending":
            raise HTTPException(
                status_code=409, detail=f"Lark bot command is not pending: {command.status}"
            )
        actor = self._resolved_actor(request.actor or command.open_id or command.actor)
        if request.require_owner:
            self.assert_actor(command, actor)
        if self._pending_command_expired(command):
            expired = repository.expire_lark_bot_pending_command(command_id)
            assert expired is not None
            raise HTTPException(status_code=409, detail="Lark bot pending command expired.")
        confirmed = repository.confirm_lark_bot_pending_command(
            command_id, actor=actor, note=request.note
        )
        if confirmed is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        if confirmed.action_kind == "spreadsheet_rerun":
            self._ensure_spreadsheet_rerun_active_run(confirmed)
            self._start_pending_command_background(command_id, actor)
            self._save_audit(
                actor=actor,
                identity=confirmed.identity,
                profile=confirmed.profile,
                operation="pending_command_confirmed",
                status="confirmed",
                context=confirmed.command_text,
                risk_action=confirmed.action_kind,
            )
            return confirmed
        try:
            execution_result = self._execute_pending_command(confirmed)
        except FileNotFoundError as exc:
            self._mark_confirm_failed(
                command_id=command_id,
                command=confirmed,
                actor=actor,
                error_message=str(exc),
                error_type="not_found",
                exc=exc,
                status_code=404,
            )
        except HTTPException as exc:
            self._mark_confirm_failed(
                command_id=command_id,
                command=confirmed,
                actor=actor,
                error_message=self._http_exception_detail_text(exc.detail),
                error_type="http_error",
                exc=exc,
            )
        except Exception as exc:
            self._mark_confirm_failed(
                command_id=command_id,
                command=confirmed,
                actor=actor,
                error_message=str(exc)[:500],
                error_type=type(exc).__name__,
                exc=exc,
                status_code=500,
            )
        completed = repository.complete_lark_bot_pending_command(
            command_id,
            status="executed",
            execution_result=execution_result,
        )
        self._save_audit(
            actor=actor,
            identity=confirmed.identity,
            profile=confirmed.profile,
            operation="pending_command_executed",
            context=confirmed.command_text,
            risk_action=confirmed.action_kind,
        )
        if completed is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        return completed

    def _mark_confirm_failed(
        self,
        *,
        command_id: str,
        command: LarkBotPendingCommand,
        actor: str,
        error_message: str,
        error_type: str,
        exc: BaseException,
        status_code: int | None = None,
    ) -> None:
        failed = self._job_repository().complete_lark_bot_pending_command(
            command_id,
            status="failed",
            error_message=error_message,
        )
        self._save_audit(
            actor=actor,
            identity=command.identity,
            profile=command.profile,
            operation="pending_command_failed",
            status="failed",
            context=command.command_text,
            risk_action=command.action_kind,
            error_type=error_type,
            hint=error_message,
        )
        if failed is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            ) from exc
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=status_code or 500, detail=error_message) from exc

    def cancel(
        self,
        command_id: str,
        request: LarkBotPendingCommandCancelRequest,
    ) -> LarkBotPendingCommand:
        repository = self._job_repository()
        command = repository.get_lark_bot_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        if command.status != "pending":
            raise HTTPException(
                status_code=409, detail=f"Lark bot command is not pending: {command.status}"
            )
        actor = self._resolved_actor(request.actor or command.open_id or command.actor)
        if request.require_owner:
            self.assert_actor(command, actor)
        cancelled = repository.cancel_lark_bot_pending_command(
            command_id,
            actor=actor,
            note=request.note,
        )
        if cancelled is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        self._save_audit(
            actor=actor,
            identity=cancelled.identity,
            profile=cancelled.profile,
            operation="pending_command_cancelled",
            context=cancelled.command_text,
            risk_action=cancelled.action_kind,
        )
        return cancelled

    def retain(
        self,
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        command = self.pending_command_for_lifecycle_action(command_id)
        actor = self._resolved_actor(request.actor or command.open_id or command.actor)
        self.assert_actor(command, actor)
        retained = self._job_repository().retain_lark_bot_pending_command(
            command_id,
            actor=actor,
            note=request.note,
        )
        if retained is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        self.resolve_cleanup_decision(
            command=retained,
            status="retained",
            actor=actor,
            note=request.note,
        )
        self._save_audit(
            actor=actor,
            identity=retained.identity,
            profile=retained.profile,
            operation="pending_command_retained",
            context=retained.command_text,
            risk_action=retained.action_kind,
        )
        return retained

    def delete(
        self,
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        command = self.pending_command_for_lifecycle_action(command_id)
        actor = self._resolved_actor(request.actor or command.open_id or command.actor)
        self.assert_actor(command, actor)
        deleted = self._job_repository().delete_lark_bot_pending_command(
            command_id,
            actor=actor,
            note=request.note,
        )
        if deleted is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        self.resolve_cleanup_decision(
            command=deleted,
            status="deleted",
            actor=actor,
            note=request.note,
        )
        self._save_audit(
            actor=actor,
            identity=deleted.identity,
            profile=deleted.profile,
            operation="pending_command_deleted",
            context=deleted.command_text,
            risk_action=deleted.action_kind,
        )
        return deleted

    def default_delete(
        self,
        command_id: str,
        request: LarkBotPendingCommandCleanupRequest,
    ) -> LarkBotPendingCommand:
        command = self.pending_command_for_lifecycle_action(command_id)
        actor = self._resolved_actor(request.actor or command.open_id or command.actor)
        self.assert_actor(command, actor)
        note = request.note or "retain/delete decision timed out"
        deleted = self._job_repository().default_delete_lark_bot_pending_command(
            command_id,
            actor=actor,
            note=note,
        )
        if deleted is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        self.resolve_cleanup_decision(
            command=deleted,
            status="default_deleted",
            actor=actor,
            note=note,
        )
        self._save_audit(
            actor=actor,
            identity=deleted.identity,
            profile=deleted.profile,
            operation="pending_command_default_deleted",
            context=deleted.command_text,
            risk_action=deleted.action_kind,
        )
        return deleted

    def pending_command_for_lifecycle_action(self, command_id: str) -> LarkBotPendingCommand:
        command = self._job_repository().get_lark_bot_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        if command.status != "pending":
            raise HTTPException(
                status_code=409, detail=f"Lark bot command is not pending: {command.status}"
            )
        return command

    def assert_actor(self, command: LarkBotPendingCommand, actor: str) -> None:
        allowed_actors = {value for value in {command.open_id, command.actor} if value}
        if command.open_id and actor not in allowed_actors:
            raise HTTPException(
                status_code=403,
                detail="Only the user who created this XiaoD pending command can operate it.",
            )

    def resolve_cleanup_decision(
        self,
        *,
        command: LarkBotPendingCommand,
        status: str,
        actor: str,
        note: str,
    ) -> None:
        decision = self._job_repository().get_pending_xiaod_decision(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="retain_or_delete_unexecuted_command",
        )
        if decision is None or decision.command_id != command.command_id:
            return
        self._job_repository().resolve_xiaod_pending_decision(
            decision.decision_id,
            status=status,
            actor=actor,
            note=note,
            payload={**decision.payload, "command_status": command.status},
        )

    def fail_background(
        self,
        *,
        command: LarkBotPendingCommand,
        actor: str,
        error_message: str,
        error_type: str,
    ) -> None:
        repository = self._job_repository()
        repository.complete_lark_bot_pending_command(
            command.command_id,
            status="failed",
            error_message=error_message,
        )
        self._save_audit(
            actor=actor,
            identity=command.identity,
            profile=command.profile,
            operation="pending_command_failed",
            status="failed",
            context=command.command_text,
            risk_action=command.action_kind,
            error_type=error_type,
            hint=error_message,
        )
        run = self._active_spreadsheet_rerun_run_for_command(command)
        if run is None:
            return
        summary = dict(getattr(run, "summary", {}) or {})
        summary.update(
            {
                "stage": "failed",
                "error_message": error_message,
                "error_type": error_type,
            }
        )
        repository.complete_xiaod_execution_run(
            str(getattr(run, "run_id", "")),
            status="failed",
            summary=summary,
        )

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.lark_bot_routes import (
    LarkBotPendingCommandCleanupRequest,
    LarkBotPendingCommandConfirmRequest,
)
from debug_agent.api.lark_pending_command_execution import (
    payload_dict,
    payload_dict_list,
    payload_string,
)
from debug_agent.lark.bot import (
    LarkBotReplyPayload,
    build_lark_bot_pending_command_reply,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand
from debug_agent.xiaod.schemas import XiaoDTurnHandleRequest


WRITEBACK_DECISION_RECOVERY_WINDOW = timedelta(minutes=30)


class XiaoDPendingInteractionController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        resolved_actor: Callable[[str], str],
        pending_command_expired: Callable[[LarkBotPendingCommand], bool],
        default_delete_pending_command: Callable[
            [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
        ],
        confirm_pending_command: Callable[
            [str, LarkBotPendingCommandConfirmRequest], LarkBotPendingCommand
        ],
        retain_pending_command: Callable[
            [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
        ],
        delete_pending_command: Callable[
            [str, LarkBotPendingCommandCleanupRequest], LarkBotPendingCommand
        ],
        assert_pending_command_actor: Callable[[LarkBotPendingCommand, str], None],
        resolve_writeback_decision: Callable[..., dict[str, object]],
        writeback_decision_markdown: Callable[..., str],
    ) -> None:
        self._job_repository = job_repository
        self._resolved_actor = resolved_actor
        self._pending_command_expired = pending_command_expired
        self._default_delete_pending_command = default_delete_pending_command
        self._confirm_pending_command = confirm_pending_command
        self._retain_pending_command = retain_pending_command
        self._delete_pending_command = delete_pending_command
        self._assert_pending_command_actor = assert_pending_command_actor
        self._resolve_writeback_decision = resolve_writeback_decision
        self._writeback_decision_markdown = writeback_decision_markdown

    def sweep_expired_decisions(self, *, limit: int = 50) -> dict[str, int]:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        cleanup_count = 0
        no_sync_count = 0
        stale_count = 0
        repository = self._job_repository()
        decisions = repository.list_pending_xiaod_decisions(
            expires_before=now,
            limit=limit,
        )
        for decision in decisions:
            if decision.decision_kind == "retain_or_delete_unexecuted_command":
                command = repository.get_lark_bot_pending_command(decision.command_id)
                if command is None or command.status != "pending":
                    repository.resolve_xiaod_pending_decision(
                        decision.decision_id,
                        status="stale",
                        actor="xiaod-timeout-sweeper",
                        note="Pending command is no longer active.",
                    )
                    stale_count += 1
                    continue
                try:
                    self._default_delete_pending_command(
                        decision.command_id,
                        LarkBotPendingCommandCleanupRequest(
                            actor=decision.open_id,
                            note="retain/delete decision timed out",
                        ),
                    )
                    cleanup_count += 1
                except HTTPException:
                    repository.resolve_xiaod_pending_decision(
                        decision.decision_id,
                        status="stale",
                        actor="xiaod-timeout-sweeper",
                        note="Default delete skipped because command is no longer pending.",
                    )
                    stale_count += 1
            elif decision.decision_kind == "spreadsheet_rerun_writeback_sync":
                command = repository.get_lark_bot_pending_command(decision.command_id)
                if command is None:
                    repository.resolve_xiaod_pending_decision(
                        decision.decision_id,
                        status="stale",
                        actor="xiaod-timeout-sweeper",
                        note="Pending command is missing.",
                    )
                    stale_count += 1
                    continue
                self._resolve_writeback_decision(
                    command=command,
                    decision=decision,
                    actor=decision.open_id or command.open_id or command.actor,
                    sync_requested=False,
                    default_skip=True,
                )
                no_sync_count += 1
        return {
            "default_deleted": cleanup_count,
            "default_no_sync": no_sync_count,
            "stale": stale_count,
        }

    def active_pending_command(
        self,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotPendingCommand | None:
        if not request.chat_id or not request.open_id:
            return None
        active_commands = self._job_repository().list_active_lark_bot_pending_commands_for_user(
            tenant_key=request.tenant_key,
            chat_id=request.chat_id,
            open_id=request.open_id,
            limit=50,
        )
        fresh_command: LarkBotPendingCommand | None = None
        for command in active_commands:
            if not self._pending_command_expired(command):
                if fresh_command is None:
                    fresh_command = command
                continue
            self.default_delete_expired_pending_command(command, request)
        return fresh_command

    def default_delete_expired_pending_command(
        self,
        command: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
    ) -> None:
        actor = self._resolved_actor(
            request.actor or request.open_id or command.open_id or command.actor
        )
        self._default_delete_pending_command(
            command.command_id,
            LarkBotPendingCommandCleanupRequest(
                actor=actor,
                note="Expired XiaoD pending command cleaned before handling a new message.",
            ),
        )

    def pending_spreadsheet_rerun_writeback_decision(
        self,
        request: XiaoDTurnHandleRequest,
    ) -> object | None:
        if not request.chat_id or not request.open_id:
            return None
        repository = self._job_repository()
        decision = repository.get_pending_xiaod_decision(
            tenant_key=request.tenant_key,
            chat_id=request.chat_id,
            open_id=request.open_id,
            decision_kind="spreadsheet_rerun_writeback_sync",
        )
        if decision is not None:
            return decision
        return self.recover_pending_writeback_decision_from_active_run(request)

    def recover_pending_writeback_decision_from_active_run(
        self,
        request: XiaoDTurnHandleRequest,
    ) -> object | None:
        repository = self._job_repository()
        run = repository.get_active_xiaod_execution_run(
            tenant_key=request.tenant_key,
            chat_id=request.chat_id,
            open_id=request.open_id,
        )
        if run is None or run.action_kind != "spreadsheet_rerun":
            return None
        summary = run.summary if isinstance(run.summary, dict) else {}
        if str(summary.get("writeback_decision_status") or "") != "pending":
            return None
        if self.writeback_decision_recovery_expired(run):
            return None
        command_id = payload_string(summary.get("command_id")) or run.command_id
        if not command_id:
            return None
        row_results = payload_dict_list(summary.get("row_results"))
        report_count = int(summary.get("report_count") or 0)
        decision = repository.create_xiaod_pending_decision(
            decision_id=str(uuid4()),
            tenant_key=run.tenant_key,
            chat_id=run.chat_id,
            open_id=run.open_id,
            decision_kind="spreadsheet_rerun_writeback_sync",
            command_id=command_id,
            run_id=run.run_id,
            payload={
                "row_results": row_results,
                "report_count": report_count,
                "default": "no_sync",
            },
            note="Recovered pending spreadsheet sync decision from active XiaoD run.",
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds"),
        )
        repository.save_xiaod_command_audit(
            tenant_key=run.tenant_key,
            chat_id=run.chat_id,
            open_id=run.open_id,
            command_id=command_id,
            run_id=run.run_id,
            decision_id=decision.decision_id,
            event_kind="spreadsheet_rerun_writeback_decision_recovered",
            status="pending",
            actor=request.open_id,
            reason="active_run_summary",
            payload={"row_results": row_results, "report_count": report_count},
        )
        return decision

    @staticmethod
    def writeback_decision_recovery_expired(run: object) -> bool:
        timestamp = payload_string(getattr(run, "updated_at", "")) or payload_string(
            getattr(run, "created_at", "")
        )
        if not timestamp:
            return True
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return datetime.now(UTC) - parsed > WRITEBACK_DECISION_RECOVERY_WINDOW

    def spreadsheet_rerun_writeback_decision_payload(
        self,
        request: XiaoDTurnHandleRequest,
        sync_requested: bool,
    ) -> LarkBotReplyPayload:
        action_kind = "sync_writeback_decision" if sync_requested else "skip_writeback_decision"
        decision = self.pending_spreadsheet_rerun_writeback_decision(request)
        if decision is None:
            return self.turn_action_payload(
                request=request,
                action_kind=action_kind,
                status="not_found",
                markdown=(
                    "我在当前会话里没有找到等待同步决策的表格批处理。\n\n"
                    "如果你刚才是在问历史写回状态，可以问“最近任务”或给出具体 batch/job 编号。"
                ),
            )
        command_id = str(getattr(decision, "command_id", ""))
        command = self._job_repository().get_lark_bot_pending_command(command_id)
        if command is None:
            return self.turn_action_payload(
                request=request,
                action_kind=action_kind,
                status="not_found",
                markdown=f"同步决策关联的待确认操作不存在：`{command_id}`。",
            )
        actor = self._resolved_actor(request.actor or request.open_id)
        self._assert_pending_command_actor(command, actor)
        result = self._resolve_writeback_decision(
            command=command,
            decision=decision,
            actor=actor,
            sync_requested=sync_requested,
            default_skip=False,
        )
        return self.turn_action_payload(
            request=request,
            action_kind=action_kind,
            status=str(result["status"]),
            markdown=self._writeback_decision_markdown(
                command=command,
                status=str(result["status"]),
                row_results=payload_dict_list(result.get("row_results")),
                default_skip=False,
                completed_summary=payload_dict(result.get("completed_summary")),
            ),
        )

    def turn_action_payload(
        self,
        *,
        request: XiaoDTurnHandleRequest,
        action_kind: str,
        status: str,
        markdown: str,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-{action_kind}-{uuid4()}",
            action_kind=action_kind,
            status=status,
            target_type=self.reply_target_type(request),
            message_id=request.message_id,
            chat_id=request.chat_id,
            user_id=request.open_id,
            markdown=markdown,
            idempotency_key=lark_bot_idempotency_key(action_kind),
        )
        return payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(
                    payload,
                    identity=request.identity,
                    dry_run=False,
                )
            }
        )

    def continue_pending_command_payload(
        self,
        pending: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotReplyPayload:
        confirmed = self._confirm_pending_command(
            pending.command_id,
            LarkBotPendingCommandConfirmRequest(
                actor=request.actor or request.open_id,
                note="Continued from XiaoD pending continuation.",
                require_owner=True,
            ),
        )
        return build_lark_bot_pending_command_reply(
            confirmed,
            identity=confirmed.identity,
            dry_run=False,
        )

    def decline_pending_command_payload(
        self,
        pending: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotReplyPayload:
        repository = self._job_repository()
        decision = repository.get_pending_xiaod_decision(
            tenant_key=pending.tenant_key,
            chat_id=pending.chat_id,
            open_id=pending.open_id,
            decision_kind="retain_or_delete_unexecuted_command",
        )
        if decision is None:
            repository.create_xiaod_pending_decision(
                decision_id=str(uuid4()),
                tenant_key=pending.tenant_key,
                chat_id=pending.chat_id,
                open_id=pending.open_id,
                decision_kind="retain_or_delete_unexecuted_command",
                command_id=pending.command_id,
                payload={"action_kind": pending.action_kind, "command_text": pending.command_text},
                note="User declined continuation; waiting for retain/delete.",
                expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(
                    timespec="seconds"
                ),
            )
        return self.pending_command_action_payload(
            command=pending,
            request=request,
            action_kind="decline_pending_command",
            markdown=(
                "已暂停继续执行这条未处理操作。\n\n"
                f"- 待确认编号：`{pending.command_id}`\n"
                "- 请继续选择：`保留稍后处理` 或 `彻底删除`。"
            ),
            content=self.pending_cleanup_decision_card(pending),
        )

    def retain_pending_command_payload(
        self,
        pending: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotReplyPayload:
        retained = self._retain_pending_command(
            pending.command_id,
            LarkBotPendingCommandCleanupRequest(
                actor=request.actor or request.open_id,
                note="Retained from XiaoD pending continuation.",
            ),
        )
        return self.pending_command_action_payload(
            command=retained,
            request=request,
            action_kind="retain_pending_command",
            markdown=(
                "已保留这条未执行操作，后续不会再主动提醒。\n\n"
                f"- 待确认编号：`{retained.command_id}`\n"
                f"- 当前状态：`{retained.status}`"
            ),
        )

    def delete_pending_command_payload(
        self,
        pending: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
    ) -> LarkBotReplyPayload:
        deleted = self._delete_pending_command(
            pending.command_id,
            LarkBotPendingCommandCleanupRequest(
                actor=request.actor or request.open_id,
                note="Deleted from XiaoD pending continuation.",
            ),
        )
        return self.pending_command_action_payload(
            command=deleted,
            request=request,
            action_kind="delete_pending_command",
            markdown=(
                "已彻底删除这条未执行操作，并写入审计。\n\n"
                f"- 待确认编号：`{deleted.command_id}`\n"
                f"- 当前状态：`{deleted.status}`"
            ),
        )

    def pending_command_action_payload(
        self,
        *,
        command: LarkBotPendingCommand,
        request: XiaoDTurnHandleRequest,
        action_kind: str,
        markdown: str,
        content: dict[str, object] | None = None,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-{action_kind}-{uuid4()}",
            action_kind=action_kind,
            status=command.status,
            target_type=self.reply_target_type(request),
            message_id=request.message_id,
            chat_id=request.chat_id,
            user_id=request.open_id,
            markdown=markdown,
            message_type="interactive" if content else "post",
            content=content or {},
            idempotency_key=lark_bot_idempotency_key(action_kind),
        )
        return payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(
                    payload,
                    identity=request.identity,
                    dry_run=False,
                )
            }
        )

    def pending_cleanup_decision_card(self, command: LarkBotPendingCommand) -> dict[str, object]:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "orange",
                "title": {"tag": "plain_text", "content": "保留还是删除未执行任务？"},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": (
                        f"待确认编号：`{command.command_id}`\n\n"
                        "保留后不再主动提醒；彻底删除会进入终态并写入审计。"
                    ),
                },
                {
                    "tag": "action",
                    "actions": [
                        self.pending_lifecycle_button(
                            label="保留稍后处理",
                            action="retain_pending_command",
                            command_id=command.command_id,
                        ),
                        self.pending_lifecycle_button(
                            label="彻底删除",
                            action="delete_pending_command",
                            command_id=command.command_id,
                            style="danger",
                        ),
                    ],
                },
            ],
        }

    @staticmethod
    def pending_lifecycle_button(
        *,
        label: str,
        action: str,
        command_id: str,
        style: str = "default",
    ) -> dict[str, object]:
        value = {"action": action, "command_id": command_id}
        return {
            "tag": "button",
            "text": {"tag": "plain_text", "content": label},
            "type": style,
            "value": value,
            "behaviors": [{"type": "callback", "value": value}],
        }

    @staticmethod
    def reply_target_type(
        request: XiaoDTurnHandleRequest,
    ) -> Literal["message", "chat", "user", "none"]:
        if request.message_id:
            return "message"
        if request.chat_id:
            return "chat"
        if request.open_id:
            return "user"
        return "none"

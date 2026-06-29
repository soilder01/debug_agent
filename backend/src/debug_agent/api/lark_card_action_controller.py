from __future__ import annotations

from collections.abc import Callable
from typing import Literal, cast
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.badcase_intake_parsers import _object_int, _object_string
from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCancelRequest,
    LarkBotBadcaseDraftConfirmRequest,
    LarkBotPendingCommandCancelRequest,
    LarkBotPendingCommandCleanupRequest,
    LarkBotPendingCommandConfirmRequest,
)
from debug_agent.api.schemas import (
    RecommendedActionStatusRequest,
    RecommendedActionVerificationRequest,
)
from debug_agent.jobs.service import SubmittedDebugJob
from debug_agent.lark.bot import (
    LarkBotReplyPayload,
    build_lark_bot_pending_command_reply,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.storage.repository import LarkBotBadcaseDraft, LarkBotPendingCommand


class LarkCardActionController:
    def __init__(
        self,
        *,
        confirm_pending_command: Callable[[str, LarkBotPendingCommandConfirmRequest], object],
        cancel_pending_command: Callable[[str, LarkBotPendingCommandCancelRequest], object],
        retain_pending_command: Callable[[str, LarkBotPendingCommandCleanupRequest], object],
        delete_pending_command: Callable[[str, LarkBotPendingCommandCleanupRequest], object],
        default_delete_pending_command: Callable[
            [str, LarkBotPendingCommandCleanupRequest], object
        ],
        pending_command_for_lifecycle_action: Callable[[str], LarkBotPendingCommand],
        assert_pending_command_actor: Callable[[LarkBotPendingCommand, str], None],
        create_pending_command_cleanup_decision: Callable[[LarkBotPendingCommand], None],
        pending_command_action_reply: Callable[
            [LarkBotPendingCommand, str, str, dict[str, object] | None],
            LarkBotReplyPayload,
        ],
        pending_cleanup_decision_card: Callable[[LarkBotPendingCommand], dict[str, object]],
        get_pending_command: Callable[[str], LarkBotPendingCommand | None],
        get_pending_writeback_decision: Callable[[LarkBotPendingCommand], object | None],
        resolve_writeback_decision: Callable[
            [LarkBotPendingCommand, object, str, bool, bool], dict[str, object]
        ],
        writeback_decision_markdown: Callable[
            [LarkBotPendingCommand, str, list[dict[str, object]], bool, dict[str, object] | None],
            str,
        ],
        payload_dict: Callable[[object], dict[str, object]],
        payload_dict_list: Callable[[object], list[dict[str, object]]],
        confirm_badcase_draft: Callable[[str, LarkBotBadcaseDraftConfirmRequest], object],
        cancel_badcase_draft: Callable[[str, LarkBotBadcaseDraftCancelRequest], object],
        reply_target_type: Callable[
            [LarkBotBadcaseDraft], Literal["message", "chat", "user", "none"]
        ],
        default_actor: str,
        update_recommended_action_status: Callable[
            [str, int, RecommendedActionStatusRequest], object
        ],
        create_recommended_action_verification_job: Callable[
            [str, int, RecommendedActionVerificationRequest], object
        ],
    ) -> None:
        self._confirm_pending_command = confirm_pending_command
        self._cancel_pending_command = cancel_pending_command
        self._retain_pending_command = retain_pending_command
        self._delete_pending_command = delete_pending_command
        self._default_delete_pending_command = default_delete_pending_command
        self._pending_command_for_lifecycle_action = pending_command_for_lifecycle_action
        self._assert_pending_command_actor = assert_pending_command_actor
        self._create_pending_command_cleanup_decision = create_pending_command_cleanup_decision
        self._pending_command_action_reply = pending_command_action_reply
        self._pending_cleanup_decision_card = pending_cleanup_decision_card
        self._get_pending_command = get_pending_command
        self._get_pending_writeback_decision = get_pending_writeback_decision
        self._resolve_writeback_decision = resolve_writeback_decision
        self._writeback_decision_markdown = writeback_decision_markdown
        self._payload_dict = payload_dict
        self._payload_dict_list = payload_dict_list
        self._confirm_badcase_draft = confirm_badcase_draft
        self._cancel_badcase_draft = cancel_badcase_draft
        self._reply_target_type = reply_target_type
        self._default_actor = default_actor
        self._update_recommended_action_status = update_recommended_action_status
        self._create_recommended_action_verification_job = (
            create_recommended_action_verification_job
        )

    def handle_card_action_event(self, payload: dict[str, object]) -> dict[str, object] | None:
        event_type = self.event_type(payload)
        if "card" not in event_type or "action" not in event_type:
            return None
        value = self.card_action_value(payload)
        action = _object_string(value, "action")
        draft_id = _object_string(value, "draft_id")
        command_id = _object_string(value, "command_id")
        if action in {"action_queue_accept", "action_queue_verify", "action_queue_manual"}:
            return self.handle_action_queue_card_action(
                event_type=event_type,
                payload=payload,
                value=value,
                action=action,
            )
        if action == "confirm_pending_command" and command_id:
            return self._handle_confirm_pending(event_type, payload, action, command_id)
        if action == "cancel_pending_command" and command_id:
            return self._handle_cancel_pending(event_type, payload, action, command_id)
        if (
            action
            in {
                "continue_pending_command",
                "decline_pending_command",
                "retain_pending_command",
                "delete_pending_command",
                "default_delete_pending_command",
            }
            and command_id
        ):
            return self.handle_pending_lifecycle_card_action(
                event_type=event_type,
                payload=payload,
                action=action,
                command_id=command_id,
            )
        if (
            action
            in {
                "sync_spreadsheet_rerun_writeback",
                "skip_spreadsheet_rerun_writeback",
                "default_skip_spreadsheet_rerun_writeback",
            }
            and command_id
        ):
            return self.handle_spreadsheet_rerun_writeback_card_action(
                event_type=event_type,
                payload=payload,
                action=action,
                command_id=command_id,
            )
        if action not in {"confirm_badcase_draft", "cancel_badcase_draft"} or not draft_id:
            return {
                "event_type": event_type,
                "handled": False,
                "ignored_reason": "unsupported_card_action",
            }
        actor = self.card_action_actor(payload)
        if action == "confirm_badcase_draft":
            confirmed = self._confirm_badcase_draft(
                draft_id,
                LarkBotBadcaseDraftConfirmRequest(
                    actor=actor,
                    note="Confirmed from Lark interactive card.",
                    create_job=True,
                ),
            )
            return {
                "event_type": event_type,
                "handled": True,
                "action": action,
                "draft": confirmed.draft.model_dump(mode="json"),
                "submitted_job": confirmed.submitted_job.model_dump(mode="json")
                if confirmed.submitted_job is not None
                else None,
                "reply": self.card_action_progress_payload(
                    action=action,
                    draft=confirmed.draft,
                    submitted_job=confirmed.submitted_job,
                ).model_dump(mode="json"),
                "toast": {"type": "success", "content": "已提交 Debug 任务。"},
            }
        cancelled = self._cancel_badcase_draft(
            draft_id,
            LarkBotBadcaseDraftCancelRequest(
                actor=actor,
                note="Cancelled from Lark interactive card.",
            ),
        )
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "draft": cancelled.model_dump(mode="json"),
            "reply": self.card_action_progress_payload(
                action=action,
                draft=cancelled,
                submitted_job=None,
            ).model_dump(mode="json"),
            "toast": {"type": "success", "content": "已取消 badcase 草稿。"},
        }

    def _handle_confirm_pending(
        self, event_type: str, payload: dict[str, object], action: str, command_id: str
    ) -> dict[str, object]:
        actor = self.card_action_actor(payload)
        confirmed = self._confirm_pending_command(
            command_id,
            LarkBotPendingCommandConfirmRequest(
                actor=actor,
                note="Confirmed from Lark interactive task card.",
            ),
        )
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "pending_command": confirmed.model_dump(mode="json"),
            "reply": build_lark_bot_pending_command_reply(
                confirmed,
                identity="bot",
                dry_run=False,
            ).model_dump(mode="json"),
            "toast": {"type": "success", "content": "已确认并提交 Debug 任务。"},
        }

    def _handle_cancel_pending(
        self, event_type: str, payload: dict[str, object], action: str, command_id: str
    ) -> dict[str, object]:
        actor = self.card_action_actor(payload)
        cancelled = self._cancel_pending_command(
            command_id,
            LarkBotPendingCommandCancelRequest(
                actor=actor,
                note="Cancelled from Lark interactive task card.",
            ),
        )
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "pending_command": cancelled.model_dump(mode="json"),
            "reply": build_lark_bot_pending_command_reply(
                cancelled,
                identity="bot",
                dry_run=False,
            ).model_dump(mode="json"),
            "toast": {"type": "success", "content": "已取消待确认操作。"},
        }

    def handle_pending_lifecycle_card_action(
        self,
        *,
        event_type: str,
        payload: dict[str, object],
        action: str,
        command_id: str,
    ) -> dict[str, object]:
        actor = self.card_action_actor(payload)
        if action == "continue_pending_command":
            confirmed = self._confirm_pending_command(
                command_id,
                LarkBotPendingCommandConfirmRequest(
                    actor=actor,
                    note="Continued from XiaoD continuation card.",
                    require_owner=True,
                ),
            )
            return {
                "event_type": event_type,
                "handled": True,
                "action": action,
                "pending_command": confirmed.model_dump(mode="json"),
                "reply": build_lark_bot_pending_command_reply(
                    confirmed,
                    identity="bot",
                    dry_run=False,
                ).model_dump(mode="json"),
                "toast": {"type": "success", "content": "已继续执行待确认操作。"},
            }
        if action == "decline_pending_command":
            command = self._pending_command_for_lifecycle_action(command_id)
            self._assert_pending_command_actor(command, actor)
            self._create_pending_command_cleanup_decision(command)
            reply = self._pending_command_action_reply(
                command,
                action,
                (
                    "已暂停继续执行这条未处理操作。\n\n"
                    f"- 待确认编号：`{command.command_id}`\n"
                    "- 请继续选择：`保留稍后处理` 或 `彻底删除`。"
                ),
                self._pending_cleanup_decision_card(command),
            )
            return {
                "event_type": event_type,
                "handled": True,
                "action": action,
                "pending_command": command.model_dump(mode="json"),
                "reply": reply.model_dump(mode="json"),
                "toast": {"type": "success", "content": "已暂停，等待保留或删除选择。"},
            }
        if action == "retain_pending_command":
            command = self._retain_pending_command(
                command_id,
                LarkBotPendingCommandCleanupRequest(
                    actor=actor,
                    note="Retained from XiaoD continuation card.",
                ),
            )
            markdown = f"已保留这条未执行操作，后续不会再主动提醒。\n\n- 待确认编号：`{command_id}`"
            toast = "已保留，后续不再主动提醒。"
        elif action == "delete_pending_command":
            command = self._delete_pending_command(
                command_id,
                LarkBotPendingCommandCleanupRequest(
                    actor=actor,
                    note="Deleted from XiaoD continuation card.",
                ),
            )
            markdown = f"已彻底删除这条未执行操作，并写入审计。\n\n- 待确认编号：`{command_id}`"
            toast = "已删除待确认操作。"
        else:
            command = self._default_delete_pending_command(
                command_id,
                LarkBotPendingCommandCleanupRequest(
                    actor=actor,
                    note="Default-deleted from XiaoD continuation card.",
                ),
            )
            markdown = f"已默认删除这条未执行操作，并写入审计。\n\n- 待确认编号：`{command_id}`"
            toast = "已默认删除待确认操作。"
        reply = self._pending_command_action_reply(command, action, markdown, None)
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "pending_command": command.model_dump(mode="json"),
            "reply": reply.model_dump(mode="json"),
            "toast": {"type": "success", "content": toast},
        }

    def handle_spreadsheet_rerun_writeback_card_action(
        self,
        *,
        event_type: str,
        payload: dict[str, object],
        action: str,
        command_id: str,
    ) -> dict[str, object]:
        command = self._get_pending_command(command_id)
        if command is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot pending command not found: {command_id}"
            )
        actor = self.card_action_actor(payload)
        self._assert_pending_command_actor(command, actor)
        decision = self._get_pending_writeback_decision(command)
        if decision is None or decision.command_id != command.command_id:
            raise HTTPException(
                status_code=409,
                detail="Spreadsheet rerun writeback decision is not pending.",
            )
        sync_requested = action == "sync_spreadsheet_rerun_writeback"
        default_skip = action == "default_skip_spreadsheet_rerun_writeback"
        result = self._resolve_writeback_decision(
            command, decision, actor, sync_requested, default_skip
        )
        reply = self._pending_command_action_reply(
            command,
            action,
            self._writeback_decision_markdown(
                command,
                str(result["status"]),
                self._payload_dict_list(result.get("row_results")),
                default_skip,
                self._payload_dict(result.get("completed_summary")),
            ),
            None,
        )
        toast_content = (
            "已同步到飞书表格。"
            if result["status"] == "synced"
            else "已完成同步决策，部分行失败。"
            if result["status"] == "partially_failed"
            else "已记录不同步，默认不写回。"
        )
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "pending_command": command.model_dump(mode="json"),
            "writeback_decision": result,
            "reply": reply.model_dump(mode="json"),
            "toast": {"type": "success", "content": toast_content},
        }

    def handle_action_queue_card_action(
        self,
        *,
        event_type: str,
        payload: dict[str, object],
        value: dict[str, object],
        action: str,
    ) -> dict[str, object]:
        job_id = _object_string(value, "job_id")
        action_index = _object_int(value, "action_index")
        if not job_id or action_index is None or action_index < 0:
            return {
                "event_type": event_type,
                "handled": False,
                "ignored_reason": "invalid_action_queue_payload",
            }
        actor = self.card_action_actor(payload)
        if action == "action_queue_accept":
            status = self._update_recommended_action_status(
                job_id,
                action_index,
                RecommendedActionStatusRequest(
                    status="accepted",
                    actor=actor,
                    note="Accepted from Lark Action Queue card.",
                ),
            )
            return {
                "event_type": event_type,
                "handled": True,
                "action": action,
                "recommended_action_status": status.model_dump(mode="json"),
                "toast": {"type": "success", "content": "已接受 Action Queue 动作。"},
            }
        if action == "action_queue_manual":
            status = self._update_recommended_action_status(
                job_id,
                action_index,
                RecommendedActionStatusRequest(
                    status="rejected",
                    actor=actor,
                    note="Marked for manual handoff from Lark Action Queue card.",
                ),
            )
            return {
                "event_type": event_type,
                "handled": True,
                "action": action,
                "recommended_action_status": status.model_dump(mode="json"),
                "toast": {"type": "success", "content": "已转人工处理。"},
            }
        verification = self._create_recommended_action_verification_job(
            job_id,
            action_index,
            RecommendedActionVerificationRequest(
                actor=actor,
                note="Created from Lark Action Queue card.",
            ),
        )
        return {
            "event_type": event_type,
            "handled": True,
            "action": action,
            "recommended_action_verification": verification.model_dump(mode="json"),
            "toast": {"type": "success", "content": "已创建 Action Queue 验证任务。"},
        }

    def card_action_progress_payload(
        self,
        *,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"],
        draft: LarkBotBadcaseDraft,
        submitted_job: SubmittedDebugJob | None,
    ) -> LarkBotReplyPayload:
        if action == "confirm_badcase_draft":
            lines = [
                "已收到确认，Debug 任务已提交。",
                "",
                f"- 草稿编号：`{draft.draft_id}`",
                f"- 样本追踪号：`{draft.submitted_case_id or draft.draft_id}`",
            ]
            if submitted_job is not None:
                lines.extend(
                    [
                        f"- 任务编号：`{submitted_job.job_id}`",
                        f"- 当前状态：`{submitted_job.status}`",
                    ]
                )
            elif draft.submitted_job_id:
                lines.append(f"- 任务编号：`{draft.submitted_job_id}`")
            lines.extend(
                [
                    "",
                    "我会继续跟进后端 worker 的进度；完成后我会发回根因摘要、证据、报告入口和后续闭环选项。",
                ]
            )
            action_kind = "confirm_badcase_draft"
            status = "submitted"
        else:
            lines = [
                "已取消这条 badcase 草稿。",
                "",
                f"- 草稿编号：`{draft.draft_id}`",
                f"- 当前状态：`{draft.status}`",
            ]
            action_kind = "cancel_badcase_draft"
            status = "cancelled"
        payload = LarkBotReplyPayload(
            command_id=f"card-action-{draft.draft_id}-{uuid4()}",
            action_kind=action_kind,
            status=status,
            target_type=self._reply_target_type(draft),
            message_id=draft.message_id,
            chat_id=draft.chat_id,
            user_id=draft.open_id,
            markdown="\n".join(lines),
            idempotency_key=lark_bot_idempotency_key("card-action"),
        )
        return payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(payload, identity="bot", dry_run=False)
            }
        )

    def event_type(self, payload: dict[str, object]) -> str:
        header = payload.get("header")
        if isinstance(header, dict):
            event_type = header.get("event_type")
            if isinstance(event_type, str) and event_type.strip():
                return event_type.strip()
        event_type = payload.get("event_type")
        return event_type.strip() if isinstance(event_type, str) else ""

    def card_action_value(self, payload: dict[str, object]) -> dict[str, object]:
        event = payload.get("event")
        event_dict = event if isinstance(event, dict) else payload
        for key in ("action", "action_value", "value"):
            raw = event_dict.get(key)
            if isinstance(raw, dict):
                value = raw.get("value")
                if isinstance(value, dict):
                    return cast(dict[str, object], value)
                return cast(dict[str, object], raw)
        return {}

    def card_action_actor(self, payload: dict[str, object]) -> str:
        event = payload.get("event")
        event_dict = event if isinstance(event, dict) else payload
        for container_key in ("operator", "user", "sender"):
            container = event_dict.get(container_key)
            if not isinstance(container, dict):
                continue
            operator_id = (
                container.get("operator_id")
                or container.get("user_id")
                or container.get("sender_id")
            )
            if isinstance(operator_id, dict):
                for key in ("open_id", "user_id", "union_id"):
                    value = operator_id.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            for key in ("open_id", "user_id", "union_id"):
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return self._default_actor

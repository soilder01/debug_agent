from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import HTTPException

from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftProgressNotification,
    LarkBotBadcaseDraftProgressNotificationListResponse,
    LarkBotBadcaseDraftProgressNotifiedRequest,
)
from debug_agent.lark.bot import LarkBotReplyPayload, lark_bot_reply_cli_args
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft


class LarkProgressNotificationController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        resolved_actor: Callable[[str], str],
        lark_cli_profile: Callable[[], str],
        save_audit: Callable[..., None],
        completion_notification_ready: Callable[[DebugJobRow], bool],
        reply_target_type: Callable[
            [LarkBotBadcaseDraft], Literal["message", "chat", "user", "none"]
        ],
        progress_state: Callable[[DebugJobRow], dict[str, object] | None],
        progress_card: Callable[[DebugJobRow, dict[str, object]], dict[str, object]],
        stable_progress_idempotency_key: Callable[[str], str],
    ) -> None:
        self._job_repository = job_repository
        self._resolved_actor = resolved_actor
        self._lark_cli_profile = lark_cli_profile
        self._save_audit = save_audit
        self._completion_notification_ready = completion_notification_ready
        self._reply_target_type = reply_target_type
        self._progress_state = progress_state
        self._progress_card = progress_card
        self._stable_progress_idempotency_key = stable_progress_idempotency_key

    def list_notifications(
        self,
        *,
        limit: int = 20,
    ) -> LarkBotBadcaseDraftProgressNotificationListResponse:
        notifications: list[LarkBotBadcaseDraftProgressNotification] = []
        repository = self._job_repository()
        drafts = repository.list_lark_bot_badcase_drafts(status="submitted", limit=200)
        for draft in drafts:
            if len(notifications) >= limit:
                break
            if not draft.submitted_job_id:
                continue
            job = repository.get_job(draft.submitted_job_id)
            if job is None:
                continue
            if job.status == "completed" and self._completion_notification_ready(job):
                continue
            notification = self.notification_for_draft(draft=draft, job=job)
            if notification is not None:
                if notification.progress_key in draft.progress_notified_keys:
                    continue
                notifications.append(notification)
        return LarkBotBadcaseDraftProgressNotificationListResponse(
            notifications=notifications,
            total_count=len(notifications),
        )

    def mark_notified(
        self,
        draft_id: str,
        request: LarkBotBadcaseDraftProgressNotifiedRequest,
    ) -> LarkBotBadcaseDraft:
        repository = self._job_repository()
        draft = repository.get_lark_bot_badcase_draft(draft_id)
        if draft is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}"
            )
        progress_key = request.progress_key.strip()
        if not progress_key:
            raise HTTPException(status_code=400, detail="Progress key is required.")
        if not progress_key.startswith(f"{draft_id}:"):
            raise HTTPException(
                status_code=400, detail="Progress key does not belong to this draft."
            )
        actor = self._resolved_actor(request.actor or draft.actor or draft.open_id)
        panel_message_id = request.panel_message_id.strip()
        updated = repository.mark_lark_bot_badcase_progress_notified(
            draft_id=draft_id,
            progress_key=progress_key,
            panel_message_id=panel_message_id,
        )
        if updated is None:
            raise HTTPException(
                status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}"
            )
        repository.mark_lark_notification_outbox_sent(f"badcase-progress:{progress_key}")
        self._save_audit(
            actor=actor,
            identity="bot",
            profile=self._lark_cli_profile(),
            operation="badcase_progress_notified",
            context=progress_key,
            risk_action="im_reply",
        )
        return updated

    def notification_for_draft(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
    ) -> LarkBotBadcaseDraftProgressNotification | None:
        progress = self._progress_state(job)
        if progress is None:
            return None
        progress_key = f"{draft.draft_id}:{progress['key']}"
        task_panel_key = self.task_panel_key(job.job_id)
        task_panel_message_id = draft.progress_panel_message_id
        delivery_mode: Literal["send", "update_message"] = (
            "update_message" if task_panel_message_id else "send"
        )
        message_id = task_panel_message_id or draft.message_id
        payload = LarkBotReplyPayload(
            command_id=f"badcase-progress-{draft.draft_id}",
            action_kind="badcase_progress",
            status=str(progress["stage"]),
            delivery_mode=delivery_mode,
            target_type=self._reply_target_type(draft),
            message_id=message_id,
            chat_id=draft.chat_id,
            user_id=draft.open_id,
            markdown=self.progress_markdown(draft=draft, job=job, progress=progress),
            message_type="interactive",
            content=self._progress_card(job, progress),
            task_panel_key=task_panel_key,
            task_panel_message_id=task_panel_message_id,
            idempotency_key=self._stable_progress_idempotency_key(progress_key),
        )
        fallback_delivery_args: list[str] = []
        if delivery_mode == "update_message":
            fallback_payload = payload.model_copy(
                update={
                    "delivery_mode": "send",
                    "message_id": draft.message_id,
                    "task_panel_message_id": "",
                }
            )
            fallback_delivery_args = lark_bot_reply_cli_args(
                fallback_payload, identity="bot", dry_run=False
            )
        payload = payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(payload, identity="bot", dry_run=False),
                "fallback_delivery_args": fallback_delivery_args,
            }
        )
        return LarkBotBadcaseDraftProgressNotification(
            notification_id=f"badcase-progress:{progress_key}",
            kind="badcase_progress",
            draft_id=draft.draft_id,
            draft=draft,
            payload=payload,
            dedupe_key=progress_key,
            progress_key=progress_key,
            stage=str(progress["stage"]),
            summary=str(progress["summary"]),
            task_panel_key=task_panel_key,
            task_panel_message_id=task_panel_message_id,
            job_id=job.job_id,
            case_id=job.case_id,
            job_status=job.status,
        )

    def task_panel_key(self, job_id: str) -> str:
        return f"xiaod-task-panel:{job_id}"

    def progress_markdown(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
        progress: dict[str, object],
    ) -> str:
        return "\n".join(
            [
                f"## {progress['title']}",
                "",
                f"- 草稿编号：`{draft.draft_id}`",
                f"- 样本追踪号：`{job.case_id}`",
                f"- 任务编号：`{job.job_id}`",
                f"- 当前阶段：`{progress['stage']}`",
                f"- 进度：{progress['percent']}%",
                f"- 阶段耗时：{progress['stage_elapsed']}",
                f"- 已完成 Agent：{progress['completed_agents']}",
                f"- 预计下一步：{progress['next_step']}",
                f"- 状态：{progress['summary']}",
                f"- 说明：{progress['detail']}",
            ]
        )

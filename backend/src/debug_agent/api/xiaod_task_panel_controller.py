from __future__ import annotations

from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from debug_agent.api.lark_completion_rendering import _lark_url_button
from debug_agent.lark.bot import (
    LarkBotReplyPayload,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.lark.progress_presenter import progress_bar
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository, LarkBotBadcaseDraft
from debug_agent.xiaod.schemas import XiaoDTurnHandleRequest


class XiaoDTaskPanelController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        report_base_url: Callable[[], str],
        latest_draft_for_chat: Callable[[str, str], LarkBotBadcaseDraft | None],
        latest_submitted_draft_for_chat: Callable[[str, str], LarkBotBadcaseDraft | None],
        published_or_internal_report_url: Callable[[str], str],
        lark_bot_progress_state: Callable[[DebugJobRow], dict[str, object] | None],
        lark_progress_card_for_job: Callable[
            [DebugJobRow, dict[str, object], str], dict[str, object]
        ],
    ) -> None:
        self._job_repository = job_repository
        self._report_base_url = report_base_url
        self._latest_draft_for_chat = latest_draft_for_chat
        self._latest_submitted_draft_for_chat = latest_submitted_draft_for_chat
        self._published_or_internal_report_url = published_or_internal_report_url
        self._lark_bot_progress_state = lark_bot_progress_state
        self._lark_progress_card_for_job = lark_progress_card_for_job

    def current_progress_summary(self, *, chat_id: str, open_id: str) -> str:
        draft = self._latest_draft_for_chat(chat_id, open_id)
        if draft is None:
            return "\n".join(
                [
                    "我在当前会话里没有找到已提交的 Debug 任务。",
                    "",
                    "你可以先发 badcase、飞书表格/Base/文档链接，或直接问：最近任务。",
                ]
            )
        if not draft.submitted_job_id:
            return "\n".join(
                [
                    "当前会话里最近的 badcase 还没有提交成 Debug 任务。",
                    "",
                    f"草稿编号：`{draft.draft_id}`",
                    f"草稿状态：`{draft.status}`",
                    "如果确认无误，请回复：确认提交",
                ]
            )
        job = self._job_repository().get_job(draft.submitted_job_id)
        if job is None:
            return "\n".join(
                [
                    "我找到了最近草稿，但对应 Debug 任务不存在。",
                    "",
                    f"草稿编号：`{draft.draft_id}`",
                    f"任务编号：`{draft.submitted_job_id}`",
                ]
            )
        progress = self._lark_bot_progress_state(job)
        lines = [
            "当前任务进度",
            "",
            f"- 草稿编号：`{draft.draft_id}`",
            f"- 样本追踪号：`{job.case_id}`",
            f"- 任务编号：`{job.job_id}`",
            f"- 任务状态：`{job.status}`",
        ]
        if progress is not None:
            percent = int(progress["percent"])
            lines.extend(
                [
                    f"- 当前阶段：`{progress['stage']}`",
                    f"- 阶段标题：{progress['title']}",
                    f"- 进度：{percent}%",
                    f"- 阶段耗时：{progress['stage_elapsed']}",
                    f"- 已完成 Agent：{progress['completed_agents']}",
                    f"- 预计下一步：{progress['next_step']}",
                    f"- 状态：{progress['summary']}",
                    f"- 说明：{progress['detail']}",
                    "",
                    progress_bar(percent),
                ]
            )
            return "\n".join(lines)
        if job.status == "completed":
            lines.extend(
                [
                    "- 当前阶段：`completed`",
                    "- 状态：全链路已完成，最终报告可以查看。",
                    f"- 报告链接：{self._published_or_internal_report_url(job.job_id)}",
                ]
            )
            return "\n".join(lines)
        if job.status == "failed":
            lines.extend(
                [
                    "- 当前阶段：`failed`",
                    f"- 失败原因：{job.error_message or '未记录失败原因'}",
                ]
            )
            return "\n".join(lines)
        lines.extend(
            [
                "- 当前阶段：`unknown`",
                "- 状态：任务存在，但当前没有可展示的阶段进度。",
            ]
        )
        return "\n".join(lines)

    def current_progress_payload(self, request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload:
        draft = self._latest_submitted_draft_for_chat(request.chat_id, request.open_id)
        if draft is None or not draft.submitted_job_id:
            return self.post_reply_payload(
                request=request,
                action_kind="query_current_progress",
                markdown=self.current_progress_summary(
                    chat_id=request.chat_id,
                    open_id=request.open_id,
                ),
            )
        job = self._job_repository().get_job(draft.submitted_job_id)
        if job is None:
            return self.post_reply_payload(
                request=request,
                action_kind="query_current_progress",
                markdown=self.current_progress_summary(
                    chat_id=request.chat_id,
                    open_id=request.open_id,
                ),
            )
        markdown = self.current_progress_summary(chat_id=request.chat_id, open_id=request.open_id)
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-current-progress-{uuid4()}",
            action_kind="query_current_progress",
            status="handled",
            target_type=self.reply_target_type(request),
            message_id=request.message_id,
            chat_id=request.chat_id,
            user_id=request.open_id,
            markdown=markdown,
            message_type="interactive",
            content=self.current_progress_card(job=job, markdown=markdown),
            idempotency_key=lark_bot_idempotency_key("xiaod-current-progress"),
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

    def post_reply_payload(
        self,
        *,
        request: XiaoDTurnHandleRequest,
        action_kind: str,
        markdown: str,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-{action_kind}-{uuid4()}",
            action_kind=action_kind,
            status="handled",
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

    def current_progress_card(self, *, job: DebugJobRow, markdown: str) -> dict[str, object]:
        progress = self._lark_bot_progress_state(job)
        if progress is not None:
            return self._lark_progress_card_for_job(job, progress, "当前任务进度")
        base_url = self._report_base_url().rstrip("/")
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "当前任务进度"},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown,
                },
                {
                    "tag": "action",
                    "actions": [
                        _lark_url_button(
                            "打开任务",
                            f"{base_url}/xiaod/views/jobs/{job.job_id}",
                            style="primary",
                        ),
                        _lark_url_button(
                            "查看运行阶段",
                            f"{base_url}/xiaod/views/jobs/{job.job_id}/run-stages",
                        ),
                        _lark_url_button(
                            "打开报告",
                            self._published_or_internal_report_url(job.job_id),
                        ),
                    ],
                },
            ],
        }

    def recent_tasks_payload(self, request: XiaoDTurnHandleRequest) -> LarkBotReplyPayload:
        tasks = self.recent_task_items(chat_id=request.chat_id, open_id=request.open_id, limit=3)
        markdown = self.recent_tasks_markdown(tasks)
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-recent-tasks-{uuid4()}",
            action_kind="query_recent_tasks",
            status="handled",
            target_type=self.reply_target_type(request),
            message_id=request.message_id,
            chat_id=request.chat_id,
            user_id=request.open_id,
            markdown=markdown,
            message_type="interactive" if tasks else "post",
            content=self.recent_tasks_card(tasks) if tasks else {},
            idempotency_key=lark_bot_idempotency_key("xiaod-recent-tasks"),
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

    def current_job_control_payload(
        self,
        request: XiaoDTurnHandleRequest,
        operation: str,
    ) -> LarkBotReplyPayload:
        draft = self._latest_submitted_draft_for_chat(request.chat_id, request.open_id)
        action_kind = f"{operation}_current_job"
        if draft is None or not draft.submitted_job_id:
            return self.post_reply_payload(
                request=request,
                action_kind=action_kind,
                markdown="我在当前会话里没有找到已提交的 Debug 任务，无法执行任务控制。",
            )
        job = self._job_repository().get_job(draft.submitted_job_id)
        if job is None:
            return self.post_reply_payload(
                request=request,
                action_kind=action_kind,
                markdown=f"我找到了草稿，但对应 Debug 任务不存在：`{draft.submitted_job_id}`。",
            )
        if operation == "cancel":
            return self.update_current_job_status_payload(
                request=request,
                job=job,
                action_kind=action_kind,
                target_status="cancelled",
                title="已取消当前 Debug 任务",
                detail="任务不会再被 worker 领取；如果已在执行中，本次取消会阻止后续重新领取。",
            )
        if operation == "pause":
            return self.update_current_job_status_payload(
                request=request,
                job=job,
                action_kind=action_kind,
                target_status="paused",
                title="已暂停当前 Debug 任务",
                detail="任务会保留在当前会话，恢复前不会被 worker 继续领取。",
            )
        if operation == "resume":
            if job.status != "paused":
                return self.post_reply_payload(
                    request=request,
                    action_kind=action_kind,
                    markdown=(
                        "当前 Debug 任务不是暂停状态，不能恢复。\n\n"
                        f"- 任务编号：`{job.job_id}`\n"
                        f"- 当前状态：`{job.status}`"
                    ),
                )
            return self.update_current_job_status_payload(
                request=request,
                job=job,
                action_kind=action_kind,
                target_status="created",
                title="已恢复当前 Debug 任务",
                detail="任务已重新放回队列，等待 worker 领取执行。",
            )
        return self.post_reply_payload(
            request=request,
            action_kind=action_kind,
            markdown=f"暂不支持的任务控制操作：`{operation}`。",
        )

    def update_current_job_status_payload(
        self,
        *,
        request: XiaoDTurnHandleRequest,
        job: DebugJobRow,
        action_kind: str,
        target_status: str,
        title: str,
        detail: str,
    ) -> LarkBotReplyPayload:
        if job.status in {"completed", "failed"}:
            return self.post_reply_payload(
                request=request,
                action_kind=action_kind,
                markdown=(
                    f"当前 Debug 任务已经是终态，不能执行这个操作。\n\n"
                    f"- 任务编号：`{job.job_id}`\n"
                    f"- 当前状态：`{job.status}`"
                ),
            )
        if job.status == "cancelled" and target_status != "created":
            return self.post_reply_payload(
                request=request,
                action_kind=action_kind,
                markdown=f"当前 Debug 任务已经取消：`{job.job_id}`。",
            )
        updated = self._job_repository().update_job_status(
            job.job_id,
            target_status,
            error_message=detail if target_status == "cancelled" else "",
        )
        base_url = self._report_base_url().rstrip("/")
        markdown = "\n".join(
            [
                title,
                "",
                f"- 任务编号：`{updated.job_id}`",
                f"- 样本追踪号：`{updated.case_id}`",
                f"- 当前状态：`{updated.status}`",
                f"- 说明：{detail}",
                f"- 任务入口：{base_url}/xiaod/views/jobs/{updated.job_id}",
            ]
        )
        return self.post_reply_payload(
            request=request,
            action_kind=action_kind,
            markdown=markdown,
        )

    def recent_task_items(
        self, *, chat_id: str, open_id: str, limit: int
    ) -> list[dict[str, object]]:
        if not chat_id:
            return []
        items: list[dict[str, object]] = []
        seen_job_ids: set[str] = set()
        repository = self._job_repository()
        base_url = self._report_base_url().rstrip("/")
        for draft in repository.list_lark_bot_badcase_drafts(limit=200):
            if len(items) >= limit:
                break
            if draft.chat_id != chat_id:
                continue
            if open_id and draft.open_id != open_id:
                continue
            if not draft.submitted_job_id or draft.submitted_job_id in seen_job_ids:
                continue
            job = repository.get_job(draft.submitted_job_id)
            if job is None:
                continue
            seen_job_ids.add(job.job_id)
            progress = self._lark_bot_progress_state(job)
            stage = str(progress["stage"]) if progress is not None else job.status
            title = (
                str(progress["title"])
                if progress is not None
                else self.job_status_title(job.status)
            )
            percent = (
                int(progress["percent"])
                if progress is not None
                else self.job_status_percent(job.status)
            )
            items.append(
                {
                    "draft_id": draft.draft_id,
                    "job_id": job.job_id,
                    "case_id": job.case_id,
                    "job_status": job.status,
                    "stage": stage,
                    "title": title,
                    "percent": percent,
                    "job_url": f"{base_url}/xiaod/views/jobs/{job.job_id}",
                    "report_url": self._published_or_internal_report_url(job.job_id),
                }
            )
        return items

    def recent_tasks_markdown(self, tasks: list[dict[str, object]]) -> str:
        if not tasks:
            return "\n".join(
                [
                    "最近 Debug 任务",
                    "",
                    "我在当前会话里没有找到已提交的 Debug 任务。",
                    "你可以先发 badcase、飞书表格/Base/文档链接，确认后我会在这里追踪任务。",
                ]
            )
        lines = ["最近 Debug 任务", "", f"我在当前会话里找到最近 {len(tasks)} 个任务：", ""]
        for index, item in enumerate(tasks, start=1):
            lines.extend(
                [
                    f"{index}. `{item['job_id']}`",
                    f"   - 样本追踪号：`{item['case_id']}`",
                    f"   - 状态：`{item['job_status']}` / `{item['stage']}` / {item['percent']}%",
                    f"   - 当前说明：{item['title']}",
                    f"   - 任务链接：{item['job_url']}",
                ]
            )
        return "\n".join(lines)

    def recent_tasks_card(self, tasks: list[dict[str, object]]) -> dict[str, object]:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "最近 Debug 任务"},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": "\n\n".join(
                        self.recent_task_card_line(index=index, item=item)
                        for index, item in enumerate(tasks, start=1)
                    ),
                },
                {
                    "tag": "action",
                    "actions": self.recent_task_card_actions(tasks),
                },
            ],
        }

    def recent_task_card_actions(self, tasks: list[dict[str, object]]) -> list[dict[str, object]]:
        actions: list[dict[str, object]] = []
        base_url = self._report_base_url().rstrip("/")
        for index, item in enumerate(tasks, start=1):
            actions.extend(
                [
                    _lark_url_button(
                        f"打开任务 {index}",
                        str(item["job_url"]),
                        style="primary" if index == 1 else "default",
                    ),
                    _lark_url_button(
                        f"查看进度 {index}",
                        f"{base_url}/xiaod/views/jobs/{item['job_id']}/run-stages",
                    ),
                    _lark_url_button(f"打开报告 {index}", str(item["report_url"])),
                ]
            )
        return actions

    def recent_task_card_line(self, *, index: int, item: dict[str, object]) -> str:
        return "\n".join(
            [
                f"**{index}. `{item['case_id']}`**",
                f"- 任务：`{item['job_id']}`",
                f"- 状态：`{item['job_status']}` / `{item['stage']}` / {item['percent']}%",
                f"- 说明：{item['title']}",
            ]
        )

    def reply_target_type(
        self,
        request: XiaoDTurnHandleRequest,
    ) -> Literal["message", "chat", "user", "none"]:
        if request.message_id:
            return "message"
        if request.chat_id:
            return "chat"
        if request.open_id:
            return "user"
        return "none"

    def job_status_title(self, status: str) -> str:
        if status == "completed":
            return "已完成，最终报告可以查看。"
        if status == "failed":
            return "任务失败，需要查看错误原因。"
        if status == "created":
            return "已排队，等待 worker 执行。"
        if status == "paused":
            return "已暂停，等待用户恢复。"
        if status == "cancelled":
            return "已取消，不会继续执行。"
        return "任务存在，但当前没有阶段说明。"

    def job_status_percent(self, status: str) -> int:
        if status == "completed":
            return 100
        if status == "failed":
            return 100
        if status == "created":
            return 5
        if status == "paused":
            return 5
        if status == "cancelled":
            return 100
        return 0

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Literal

from debug_agent.api.badcase_intake_parsers import _clip_text
from debug_agent.api.lark_bot_routes import LarkBotNotificationEnvelope
from debug_agent.api.lark_completion_rendering import _lark_callback_button, _lark_url_button
from debug_agent.api.lark_pending_command_execution import (
    payload_dict_list,
    payload_string,
)
from debug_agent.lark.bot import LarkBotReplyPayload, lark_bot_reply_cli_args
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository


class XiaoDRunProgressNotificationController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        report_base_url: Callable[[], str],
    ) -> None:
        self._job_repository = job_repository
        self._report_base_url = report_base_url

    def list_notifications(self, *, limit: int = 20) -> list[LarkBotNotificationEnvelope]:
        notifications: list[LarkBotNotificationEnvelope] = []
        repository = self._job_repository()
        runs = repository.list_xiaod_execution_runs(active_only=True, limit=200)
        for run in runs:
            if len(notifications) >= limit:
                break
            if run.action_kind != "spreadsheet_rerun":
                continue
            notification = self.notification_for_run(run)
            if notification is None:
                continue
            if repository.get_lark_notification_outbox(notification.notification_id) is not None:
                continue
            notifications.append(notification)
        return notifications

    def notification_for_run(self, run: object) -> LarkBotNotificationEnvelope | None:
        progress = self.progress_state(run)
        if progress is None:
            return None
        run_id = str(getattr(run, "run_id", ""))
        progress_key = f"{run_id}:{progress['key']}"
        notification_id = f"xiaod-run-progress:{progress_key}"
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        message_id = str(summary.get("message_id") or "")
        chat_id = str(getattr(run, "chat_id", "") or summary.get("chat_id") or "")
        open_id = str(getattr(run, "open_id", "") or summary.get("open_id") or "")
        payload = LarkBotReplyPayload(
            command_id=f"xiaod-run-progress-{run_id}",
            action_kind="xiaod_run_progress",
            status=str(progress["stage"]),
            target_type=self.reply_target_type(
                message_id=message_id,
                chat_id=chat_id,
                open_id=open_id,
            ),
            message_id=message_id,
            chat_id=chat_id,
            user_id=open_id,
            markdown=self.progress_markdown(run=run, progress=progress),
            message_type="interactive",
            content=self.progress_card(run=run, progress=progress),
            task_panel_key=f"xiaod-run-panel:{run_id}",
            idempotency_key=self.stable_progress_idempotency_key(progress_key),
        )
        payload = payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(payload, identity="bot", dry_run=False)
            }
        )
        jobs = self._run_jobs(run)
        first_job = jobs[0] if jobs else None
        return LarkBotNotificationEnvelope(
            notification_id=notification_id,
            kind="xiaod_run_progress",
            payload=payload,
            dedupe_key=progress_key,
            progress_key=progress_key,
            stage=str(progress["stage"]),
            summary=str(progress["summary"]),
            task_panel_key=f"xiaod-run-panel:{run_id}",
            job_id=first_job.job_id if first_job is not None else str(getattr(run, "job_id", "")),
            case_id=first_job.case_id if first_job is not None else "",
            job_status=str(progress["stage"]),
        )

    def progress_state(self, run: object) -> dict[str, object] | None:
        jobs = self._run_jobs(run)
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        if not jobs:
            if str(summary.get("stage") or "") in {"starting", "batch_started"}:
                return self._progress_state_payload(
                    key="starting",
                    stage="starting",
                    title="表格批处理已确认，正在后台启动",
                    summary="小D已经接收确认，正在后台读取表格并创建 DebugJob。",
                    detail="这一步不会阻塞飞书会话；任务创建后会继续推送运行进度。",
                    template="blue",
                )
            return self._progress_state_payload(
                key="no-jobs",
                stage="failed",
                title="表格批处理没有创建任务",
                summary="确认后没有可跟踪的 DebugJob，请检查预检结果和执行日志。",
                detail="小D已保留这次运行记录，后续不会替用户做写回。",
                template="red",
            )
        status_counts = self._job_status_counts(jobs)
        running_count = status_counts.get("running", 0)
        completed_count = status_counts.get("completed", 0)
        total_count = len(jobs)
        report_requested = bool(summary.get("report_requested"))
        report_count = int(summary.get("report_count") or 0)
        expected_report_count = self._expected_report_count(summary=summary, total_count=total_count)
        if report_requested and report_count >= expected_report_count:
            if str(summary.get("writeback_decision_status") or "") == "pending":
                return self._progress_state_payload(
                    key="writeback-decision-pending",
                    stage="writeback_decision_pending",
                    title="Debug 报告已生成",
                    summary=f"已生成 {report_count} 份报告；同步前不会写回飞书表格。",
                    detail="请选择同步到飞书表格或不同步；超时将默认不同步。",
                    template="green",
                )
            return self._progress_state_payload(
                key="report-generated",
                stage="report_generated",
                title="Debug 报告已生成",
                summary=f"已生成 {report_count} 份报告，等待后续写回决策。",
                detail="写回需要后续显式决策；本阶段不自动同步到飞书表格。",
                template="green",
            )
        failed_jobs = [job for job in jobs if job.status == "failed"]
        if failed_jobs:
            first_failed = failed_jobs[0]
            return self._progress_state_payload(
                key=f"failed-{len(failed_jobs)}-{self._status_counts_key(status_counts)}",
                stage="failed",
                title="表格批处理有任务失败",
                summary=f"{len(failed_jobs)} 个 DebugJob 失败，首个失败任务 `{first_failed.job_id}`。",
                detail=_clip_text(first_failed.error_message or "未记录失败原因", 240),
                template="red",
            )
        if running_count:
            return self._progress_state_payload(
                key="jobs-running",
                stage="running",
                title="表格批处理正在执行",
                summary=f"{running_count} 个任务运行中，{completed_count}/{total_count} 个已完成。",
                detail="小D会继续用去重通知同步阶段变化；不会在后台替用户确认写回。",
                template="blue",
            )
        if completed_count == total_count:
            if report_requested and report_count < expected_report_count:
                return self._progress_state_payload(
                    key="report-pending",
                    stage="report_pending",
                    title="表格批处理已完成，等待报告生成",
                    summary=(
                        "所有 DebugJob 已完成，已生成 "
                        f"{report_count}/{expected_report_count} 份自动闭环报告。"
                    ),
                    detail="报告可用后再进入后续写回决策；当前不会写回飞书表格。",
                    template="yellow",
                )
            if report_requested:
                if str(summary.get("writeback_decision_status") or "") == "pending":
                    return self._progress_state_payload(
                        key="writeback-decision-pending",
                        stage="writeback_decision_pending",
                        title="Debug 报告已生成",
                        summary=f"已生成 {report_count} 份报告；同步前不会写回飞书表格。",
                        detail="请选择同步到飞书表格或不同步；超时将默认不同步。",
                        template="green",
                    )
                return self._progress_state_payload(
                    key="report-generated",
                    stage="report_generated",
                    title="Debug 报告已生成",
                    summary=f"已生成 {report_count} 份报告，等待后续写回决策。",
                    detail="写回需要后续显式决策；本阶段不自动同步到飞书表格。",
                    template="green",
                )
            return self._progress_state_payload(
                key="jobs-completed",
                stage="completed",
                title="表格批处理任务已完成",
                summary=f"{total_count} 个 DebugJob 已完成。",
                detail="本次运行未请求自动报告；没有写回动作。",
                template="green",
            )
        return self._progress_state_payload(
            key="jobs-created",
            stage="created",
            title="表格批处理任务已创建",
            summary=f"已创建 {total_count} 个 DebugJob，等待 worker 领取。",
            detail="任务已进入 Debug Agent 队列，小D会继续反馈运行进度。",
            template="blue",
        )

    def progress_markdown(self, *, run: object, progress: dict[str, object]) -> str:
        jobs = self._run_jobs(run)
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        if str(progress.get("stage") or "") in {
            "writeback_decision_pending",
            "report_generated",
        }:
            return self.final_report_markdown(run=run, progress=progress, summary=summary)
        status_counts = self._job_status_counts(jobs)
        lines = [
            f"## {progress['title']}",
            "",
            f"- 运行 ID：`{getattr(run, 'run_id', '')}`",
            f"- 批次：`{getattr(run, 'batch_id', '') or summary.get('batch_id') or '未知'}`",
            f"- 任务状态：{self._format_status_counts(status_counts)}",
            f"- 报告生成：{self._report_status_label(summary)}",
            f"- 写回决策：{self._writeback_decision_label(summary)}",
            f"- 状态：{progress['summary']}",
            f"- 说明：{progress['detail']}",
        ]
        row_results = self._display_row_results(payload_dict_list(summary.get("row_results")))
        if row_results:
            mapped_count = sum(1 for row in row_results if bool(row.get("source_mapped")))
            lines.extend(
                [
                    "",
                    f"**报告摘要**：已生成 {int(summary.get('report_count') or 0)} 份报告；"
                    f"{mapped_count}/{len(row_results)} 行有 source mapping，可被同步。",
                    "",
                    "**每行结果**",
                ]
            )
            for row in row_results[:10]:
                lines.append(
                    "- 行 `{row_id}` / `{case_id}` / `{job_id}`：报告 `{report}`，"
                    "source mapping `{mapping}`".format(
                        row_id=payload_string(row.get("row_id")) or "未知行",
                        case_id=payload_string(row.get("case_id")) or "未知样本",
                        job_id=payload_string(row.get("job_id")) or "未知任务",
                        report=payload_string(row.get("report_url")) or "未生成",
                        mapping="yes" if bool(row.get("source_mapped")) else "no",
                    )
                )
            if len(row_results) > 10:
                lines.append(f"- 其余 {len(row_results) - 10} 行请在批次页查看。")
        failed_jobs = [job for job in jobs if job.status == "failed"]
        if failed_jobs:
            lines.extend(["", "**失败任务**"])
            for job in failed_jobs[:5]:
                lines.append(
                    f"- `{job.job_id}` / `{job.case_id}`："
                    f"{_clip_text(job.error_message or '未记录失败原因', 160)}"
                )
        return "\n".join(lines)

    def final_report_markdown(
        self,
        *,
        run: object,
        progress: dict[str, object],
        summary: dict[str, object],
    ) -> str:
        row_results = self._display_row_results(payload_dict_list(summary.get("row_results")))
        first_row = row_results[0] if row_results else {}
        report_url = self._first_report_url(row_results)
        loop_summary = self._debug_loop_summary(summary)
        mapped_count = sum(1 for row in row_results if bool(row.get("source_mapped")))
        lines = [
            f"## {progress['title']}",
            "",
            f"**样本**：行 `{payload_string(first_row.get('row_id')) or '未知'}` / "
            f"`{payload_string(first_row.get('case_id')) or '未知样本'}`",
            f"**报告覆盖**：{mapped_count}/{len(row_results) if row_results else 0} 行有 source mapping。",
            f"**闭环结论**：{loop_summary}",
            f"**报告状态**：{progress['summary']}",
            "**写回默认**：不同步，必须由用户点击按钮确认。",
        ]
        if report_url:
            lines.append(f"**最终报告**：[打开报告]({report_url})")
        lines.extend(
            [
                "",
                "请先打开报告确认结论和证据链，再决定是否同步到飞书表格。",
            ]
        )
        return "\n".join(lines)

    def progress_card(self, *, run: object, progress: dict[str, object]) -> dict[str, object]:
        markdown = self.progress_markdown(run=run, progress=progress)
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        batch_id = str(getattr(run, "batch_id", "") or summary.get("batch_id") or "")
        row_results = self._display_row_results(payload_dict_list(summary.get("row_results")))
        report_url = self._first_report_url(row_results)
        if str(progress.get("stage") or "") in {
            "writeback_decision_pending",
            "report_generated",
        }:
            return self.final_report_card(
                run=run,
                progress=progress,
                summary=summary,
                row_results=row_results,
                report_url=report_url,
                batch_id=batch_id,
            )
        actions = []
        if str(summary.get("writeback_decision_status") or "") == "pending":
            command_id = payload_string(summary.get("command_id"))
            actions.extend(
                [
                    _lark_callback_button(
                        "同步到飞书表格",
                        {
                            "action": "sync_spreadsheet_rerun_writeback",
                            "command_id": command_id,
                            "run_id": str(getattr(run, "run_id", "")),
                        },
                    ),
                    _lark_callback_button(
                        "不同步",
                        {
                            "action": "skip_spreadsheet_rerun_writeback",
                            "command_id": command_id,
                            "run_id": str(getattr(run, "run_id", "")),
                        },
                    ),
                ]
            )
        if batch_id:
            actions.append(
                _lark_url_button(
                    "打开批次",
                    f"{self._report_base_url().rstrip('/')}/xiaod/views/debug-batches/{batch_id}",
                )
            )
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": str(progress.get("template", "blue")),
                "title": {"tag": "plain_text", "content": str(progress["title"])},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown,
                },
                *([{"tag": "action", "actions": actions}] if actions else []),
            ],
        }

    def final_report_card(
        self,
        *,
        run: object,
        progress: dict[str, object],
        summary: dict[str, object],
        row_results: list[dict[str, object]],
        report_url: str,
        batch_id: str,
    ) -> dict[str, object]:
        command_id = payload_string(summary.get("command_id"))
        first_row = row_results[0] if row_results else {}
        report_count = int(summary.get("report_count") or 0)
        loop_summary = self._debug_loop_summary(summary)
        mapped_count = sum(1 for row in row_results if bool(row.get("source_mapped")))
        total_rows = len(row_results)
        report_actions = []
        if report_url:
            report_actions.append(_lark_url_button("打开最终报告", report_url, style="primary"))
        if batch_id:
            report_actions.append(
                _lark_url_button(
                    "查看运行批次",
                    f"{self._report_base_url().rstrip('/')}/xiaod/views/debug-batches/{batch_id}",
                )
            )
        decision_actions = []
        if str(summary.get("writeback_decision_status") or "") == "pending":
            decision_actions.extend(
                [
                    _lark_callback_button(
                        "同步到飞书表格",
                        {
                            "action": "sync_spreadsheet_rerun_writeback",
                            "command_id": command_id,
                            "run_id": str(getattr(run, "run_id", "")),
                        },
                    ),
                    _lark_callback_button(
                        "不同步",
                        {
                            "action": "skip_spreadsheet_rerun_writeback",
                            "command_id": command_id,
                            "run_id": str(getattr(run, "run_id", "")),
                        },
                    ),
                ]
            )
        elements: list[dict[str, object]] = [
            {
                "tag": "markdown",
                "content": (
                    f"**结论摘要**\n"
                    f"- 样本：行 `{payload_string(first_row.get('row_id')) or '未知'}` / "
                    f"`{payload_string(first_row.get('case_id')) or '未知样本'}`\n"
                    f"- 闭环：{loop_summary}\n"
                    f"- 报告：已生成 {report_count} 份，覆盖 {mapped_count}/{total_rows} 行"
                ),
            },
            {"tag": "hr"},
            {
                "tag": "markdown",
                "content": (
                    "**报告入口**\n"
                    "先打开最终报告确认结论、证据链和人工复核建议，再决定是否写回表格。"
                ),
            },
            *([{"tag": "action", "actions": report_actions}] if report_actions else []),
        ]
        if decision_actions:
            elements.extend(
                [
                    {"tag": "hr"},
                    {
                        "tag": "markdown",
                        "content": (
                            "**同步决策**\n"
                            "默认不同步。只有点击“同步到飞书表格”才会写回原表。"
                        ),
                    },
                    {"tag": "action", "actions": decision_actions},
                ]
            )
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": (
                        f"**运行追踪**\n"
                        f"- 运行 ID：`{getattr(run, 'run_id', '')}`\n"
                        f"- 批次：`{batch_id or '未知'}`\n"
                        f"- 状态：{progress['summary']}"
                    ),
                },
            ]
        )
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": str(progress.get("template", "green")),
                "title": {"tag": "plain_text", "content": str(progress["title"])},
            },
            "elements": elements,
        }

    def reply_target_type(
        self,
        *,
        message_id: str,
        chat_id: str,
        open_id: str,
    ) -> Literal["message", "chat", "user", "none"]:
        if message_id:
            return "message"
        if chat_id:
            return "chat"
        if open_id:
            return "user"
        return "none"

    def stable_progress_idempotency_key(self, progress_key: str) -> str:
        digest = hashlib.sha256(progress_key.encode("utf-8")).hexdigest()[:24]
        return f"da-xiaod-run-{digest}"

    def _run_jobs(self, run: object) -> list[DebugJobRow]:
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        raw_job_ids = summary.get("job_ids", [])
        if not isinstance(raw_job_ids, list):
            raw_job_ids = []
        job_ids = [str(item).strip() for item in raw_job_ids if str(item).strip()]
        jobs: list[DebugJobRow] = []
        seen: set[str] = set()
        repository = self._job_repository()
        for job_id in job_ids:
            if job_id in seen:
                continue
            seen.add(job_id)
            job = repository.get_job(job_id)
            if job is not None:
                jobs.append(job)
        batch_id = str(getattr(run, "batch_id", "") or summary.get("batch_id") or "")
        if batch_id and not jobs:
            jobs = repository.list_jobs(artifact_group_id=batch_id, limit=1000)
        return jobs

    @staticmethod
    def _expected_report_count(*, summary: dict[str, object], total_count: int) -> int:
        row_results = payload_dict_list(summary.get("row_results"))
        mapped_count = sum(1 for row in row_results if bool(row.get("source_mapped")))
        if mapped_count:
            return mapped_count
        return total_count

    def _display_row_results(self, row_results: list[dict[str, object]]) -> list[dict[str, object]]:
        mapped_rows = [row for row in row_results if bool(row.get("source_mapped"))]
        return [self._row_with_best_report_url(row) for row in (mapped_rows or row_results)]

    def _row_with_best_report_url(self, row: dict[str, object]) -> dict[str, object]:
        job_id = payload_string(row.get("job_id"))
        if not job_id:
            return row
        document = self._job_repository().get_lark_report_document(job_id)
        if document is not None and document.status == "published" and document.document_url:
            return {**row, "report_url": document.document_url}
        report_url = payload_string(row.get("report_url"))
        if report_url.startswith("/api/artifacts/files/") or report_url.startswith("file:"):
            return {
                **row,
                "report_url": (
                    f"{self._report_base_url().rstrip('/')}/xiaod/views/jobs/{job_id}/report"
                ),
            }
        return row

    @staticmethod
    def _first_report_url(row_results: list[dict[str, object]]) -> str:
        for row in row_results:
            report_url = payload_string(row.get("report_url"))
            if report_url and report_url != "未生成":
                return report_url
        return ""

    @staticmethod
    def _debug_loop_summary(summary: dict[str, object]) -> str:
        reports = payload_dict_list(summary.get("auto_closure_reports"))
        for report in reports:
            closure = report.get("closure")
            if not isinstance(closure, dict):
                continue
            debug_loop = closure.get("debug_loop")
            if not isinstance(debug_loop, dict):
                continue
            decision = payload_string(debug_loop.get("decision"))
            iteration = int(debug_loop.get("current_iteration") or 0)
            stop_reason = payload_string(debug_loop.get("stop_reason"))
            if decision == "stopped_evidence_exhausted":
                return f"第 {iteration} 轮后证据耗尽，未验证出 supported root cause。"
            if decision == "verified_root_cause_found":
                return f"第 {iteration} 轮发现 supported root cause。"
            if decision:
                return f"第 {iteration} 轮 / {decision}" + (
                    f" / {stop_reason}" if stop_reason else ""
                )
        return "报告已生成，详见最终报告。"

    @staticmethod
    def _progress_state_payload(
        *,
        key: str,
        stage: str,
        title: str,
        summary: str,
        detail: str,
        template: str,
    ) -> dict[str, object]:
        return {
            "key": key,
            "stage": stage,
            "title": title,
            "summary": summary,
            "detail": detail,
            "template": template,
        }

    @staticmethod
    def _job_status_counts(jobs: list[DebugJobRow]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        return counts

    @staticmethod
    def _format_status_counts(counts: dict[str, int]) -> str:
        if not counts:
            return "暂无"
        return "，".join(f"{status} {counts[status]}" for status in sorted(counts))

    @staticmethod
    def _status_counts_key(counts: dict[str, int]) -> str:
        return "-".join(f"{status}-{counts[status]}" for status in sorted(counts))

    @staticmethod
    def _report_status_label(summary: dict[str, object]) -> str:
        if not summary.get("report_requested"):
            return "未请求"
        report_count = int(summary.get("report_count") or 0)
        if report_count > 0:
            return f"已生成 {report_count} 份"
        return "已请求，等待任务完成后生成"

    @staticmethod
    def _writeback_decision_label(summary: dict[str, object]) -> str:
        status = str(summary.get("writeback_decision_status") or "not_ready")
        if status == "not_requested":
            return "未请求"
        if status == "not_ready":
            return "未开始，报告可用后再决策"
        return status

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from debug_agent.api.badcase_intake_parsers import _clip_text
from debug_agent.jobs.auto_closure import (
    AutoDebugClosureResult,
    build_auto_closure_writeback_fields,
)
from debug_agent.lark.bot import (
    LarkBotReplyPayload,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.spreadsheets.writeback import SpreadsheetWritebackClient
from debug_agent.spreadsheets.writeback import build_report_writeback_fields
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand


class XiaoDSpreadsheetWritebackDecisionController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        spreadsheet_writeback_client: Callable[[], SpreadsheetWritebackClient | None],
        build_report: Callable[[str], object | None],
        reply_target_type: Callable[[LarkBotPendingCommand], str],
    ) -> None:
        self._job_repository = job_repository
        self._spreadsheet_writeback_client = spreadsheet_writeback_client
        self._build_report = build_report
        self._reply_target_type = reply_target_type

    def resolve_decision(
        self,
        *,
        command: LarkBotPendingCommand,
        decision: object,
        actor: str,
        sync_requested: bool,
        default_skip: bool,
    ) -> dict[str, object]:
        run = self.execution_run_for_decision(decision)
        summary = (
            getattr(run, "summary", {})
            if run is not None and isinstance(getattr(run, "summary", {}), dict)
            else {}
        )
        decision_payload = (
            getattr(decision, "payload", {})
            if isinstance(getattr(decision, "payload", {}), dict)
            else {}
        )
        row_results = payload_dict_list(summary.get("row_results")) or payload_dict_list(
            decision_payload.get("row_results")
        )
        mapped_row_results = [row for row in row_results if bool(row.get("source_mapped"))]
        if mapped_row_results:
            row_results = mapped_row_results
        reports = payload_dict_list(summary.get("auto_closure_reports"))
        if sync_requested:
            resolved_rows = self.sync_rows(row_results=row_results, reports=reports)
            status = self.sync_resolution_status(resolved_rows)
            reason = "user_requested_sync"
        else:
            reason = "writeback decision timed out" if default_skip else "user_skipped_sync"
            resolved_rows = self.skip_rows(row_results=row_results, reason=reason)
            status = "default_skipped" if default_skip else "skipped"
        decision_id = str(getattr(decision, "decision_id", ""))
        run_id = str(getattr(decision, "run_id", ""))
        completed_summary = self.completed_summary(
            command=command,
            run=run,
            summary=summary,
            status=status,
            reason=reason,
            resolved_rows=resolved_rows,
            sync_requested=sync_requested,
            default_skip=default_skip,
        )
        payload = {
            **(
                getattr(decision, "payload", {})
                if isinstance(getattr(decision, "payload", {}), dict)
                else {}
            ),
            "row_results": resolved_rows,
            "sync_requested": sync_requested,
            "default_skip": default_skip,
            "completed_summary": completed_summary,
        }
        repository = self._job_repository()
        repository.resolve_xiaod_pending_decision(
            decision_id,
            status=status,
            actor=actor,
            note=reason,
            payload=payload,
        )
        updated_summary = {
            **summary,
            "writeback_decision_status": status,
            "writeback_results": resolved_rows,
            "completed_summary": completed_summary,
        }
        if run_id:
            repository.complete_xiaod_execution_run(
                run_id,
                status="completed",
                summary=updated_summary,
            )
        repository.save_xiaod_command_audit(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            command_id=command.command_id,
            run_id=run_id,
            decision_id=decision_id,
            event_kind="spreadsheet_rerun_writeback_decision_resolved",
            status=status,
            actor=actor,
            reason=reason,
            payload={"row_results": resolved_rows, "completed_summary": completed_summary},
        )
        repository.save_xiaod_command_audit(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            command_id=command.command_id,
            run_id=run_id,
            decision_id=decision_id,
            event_kind="xiaod_run_completed",
            status="completed",
            actor=actor,
            reason=reason,
            payload=completed_summary,
        )
        return {
            "decision_id": decision_id,
            "run_id": run_id,
            "status": status,
            "row_results": resolved_rows,
            "completed_summary": completed_summary,
        }

    def completed_summary(
        self,
        *,
        command: LarkBotPendingCommand,
        run: object | None,
        summary: dict[str, object],
        status: str,
        reason: str,
        resolved_rows: list[dict[str, object]],
        sync_requested: bool,
        default_skip: bool,
    ) -> dict[str, object]:
        raw_job_ids = summary.get("job_ids", [])
        if not isinstance(raw_job_ids, list):
            raw_job_ids = []
        job_ids = [payload_string(item) for item in raw_job_ids if payload_string(item)]
        writeback_status_counts: dict[str, int] = {}
        for row in resolved_rows:
            row_status = payload_string(row.get("writeback_status")) or "unknown"
            writeback_status_counts[row_status] = writeback_status_counts.get(row_status, 0) + 1
        batch_id = payload_string(summary.get("batch_id")) or str(
            getattr(run, "batch_id", "") if run is not None else ""
        )
        return {
            "headline": "XiaoD run completed",
            "status": "completed",
            "run_id": str(getattr(run, "run_id", "") if run is not None else ""),
            "command_id": command.command_id,
            "batch_id": batch_id,
            "job_count": len(job_ids),
            "report_count": int(summary.get("report_count") or 0),
            "row_count": len(resolved_rows),
            "writeback_decision_status": status,
            "writeback_status_counts": writeback_status_counts,
            "sync_requested": sync_requested,
            "default_skip": default_skip,
            "reason": reason,
            "completed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }

    def execution_run_for_decision(self, decision: object) -> object | None:
        run_id = str(getattr(decision, "run_id", ""))
        if not run_id:
            return None
        repository = self._job_repository()
        for run in repository.list_xiaod_execution_runs(active_only=True, limit=500):
            if run.run_id == run_id:
                return run
        for run in repository.list_xiaod_execution_runs(limit=500):
            if run.run_id == run_id:
                return run
        return None

    def sync_rows(
        self,
        *,
        row_results: list[dict[str, object]],
        reports: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        reports_by_job_id = {
            payload_string(report.get("job_id")): report
            for report in reports
            if payload_string(report.get("job_id"))
        }
        resolved: list[dict[str, object]] = []
        for row in row_results:
            job_id = payload_string(row.get("job_id"))
            row_id = payload_string(row.get("row_id"))
            report_url = self.best_report_url(
                job_id=job_id,
                fallback_url=payload_string(row.get("report_url")),
            )
            if not job_id or not bool(row.get("source_mapped")):
                resolved.append(
                    self.record_skip(
                        row=row,
                        status="skipped_no_mapping",
                        reason="source mapping missing",
                    )
                )
                continue
            writeback_client = self._spreadsheet_writeback_client()
            if writeback_client is None:
                resolved.append(
                    self.record_failure(
                        row=row,
                        report_url=report_url,
                        error_message="Spreadsheet writeback client is not configured",
                    )
                )
                continue
            report = self._build_report(job_id)
            if report is None:
                resolved.append(
                    self.record_failure(
                        row=row,
                        report_url=report_url,
                        error_message=f"Debug report not found for job: {job_id}",
                    )
                )
                continue
            fields = build_report_writeback_fields(report, report_url=report_url)
            closure_payload = payload_dict(reports_by_job_id.get(job_id, {}).get("closure"))
            if closure_payload:
                fields.update(
                    build_auto_closure_writeback_fields(
                        AutoDebugClosureResult.model_validate(closure_payload)
                    )
                )
            try:
                written_fields = writeback_client.update_row(
                    spreadsheet_id=payload_string(row.get("spreadsheet_id")),
                    sheet_id=payload_string(row.get("sheet_id")),
                    row_id=row_id,
                    fields=fields,
                )
            except Exception as exc:  # noqa: BLE001
                resolved.append(
                    self.record_failure(
                        row=row,
                        report_url=report_url,
                        error_message=str(exc)[:500],
                    )
                )
                continue
            final_fields = written_fields or fields
            self._job_repository().save_spreadsheet_writeback_audit(
                job_id=job_id,
                status="succeeded",
                row_id=row_id,
                report_url=report_url,
                fields=final_fields,
                error_message="",
            )
            self.save_stage(
                row=row,
                status="completed",
                report_url=report_url,
                output={"writeback_status": "succeeded", "report_url": report_url},
                failure_reason="",
            )
            resolved.append({**row, "writeback_status": "succeeded", "fields": final_fields})
        return resolved

    def best_report_url(self, *, job_id: str, fallback_url: str) -> str:
        document = self._job_repository().get_lark_report_document(job_id) if job_id else None
        if document is not None and document.status == "published" and document.document_url:
            return document.document_url
        if fallback_url.startswith("/api/artifacts/files/") or fallback_url.startswith("file:"):
            return fallback_url
        return fallback_url

    def skip_rows(
        self, *, row_results: list[dict[str, object]], reason: str
    ) -> list[dict[str, object]]:
        return [self.record_skip(row=row, status="skipped", reason=reason) for row in row_results]

    def record_skip(self, *, row: dict[str, object], status: str, reason: str) -> dict[str, object]:
        job_id = payload_string(row.get("job_id"))
        report_url = payload_string(row.get("report_url"))
        row_id = payload_string(row.get("row_id"))
        if job_id:
            self._job_repository().save_spreadsheet_writeback_audit(
                job_id=job_id,
                status="skipped",
                row_id=row_id,
                report_url=report_url,
                fields={},
                error_message=reason,
            )
            self.save_stage(
                row=row,
                status="skipped",
                report_url=report_url,
                output={"writeback_status": status, "report_url": report_url},
                failure_reason=reason,
            )
        return {**row, "writeback_status": status, "error_message": reason}

    def record_failure(
        self,
        *,
        row: dict[str, object],
        report_url: str,
        error_message: str,
    ) -> dict[str, object]:
        job_id = payload_string(row.get("job_id"))
        row_id = payload_string(row.get("row_id"))
        if job_id:
            self._job_repository().save_spreadsheet_writeback_audit(
                job_id=job_id,
                status="failed",
                row_id=row_id,
                report_url=report_url,
                fields={},
                error_message=error_message,
            )
            self.save_stage(
                row=row,
                status="failed",
                report_url=report_url,
                output={"writeback_status": "failed", "report_url": report_url},
                failure_reason=error_message,
            )
        return {**row, "writeback_status": "failed", "error_message": error_message}

    def save_stage(
        self,
        *,
        row: dict[str, object],
        status: str,
        report_url: str,
        output: dict[str, object],
        failure_reason: str,
    ) -> None:
        job_id = payload_string(row.get("job_id"))
        if not job_id:
            return
        self._job_repository().save_debug_run_stage(
            job_id=job_id,
            stage="writeback",
            status=status,
            input={"requested": True, "report_url": report_url},
            output=output,
            failure_reason=failure_reason,
            retryable=status == "failed",
        )

    def sync_resolution_status(self, row_results: list[dict[str, object]]) -> str:
        statuses = {payload_string(row.get("writeback_status")) for row in row_results}
        if "failed" in statuses:
            return "partially_failed"
        if "succeeded" in statuses:
            return "synced"
        return "skipped"

    def decision_markdown(
        self,
        *,
        command: LarkBotPendingCommand,
        status: str,
        row_results: list[dict[str, object]],
        default_skip: bool,
        completed_summary: dict[str, object] | None = None,
    ) -> str:
        lines = [
            "表格批处理同步决策已处理。",
            "",
            f"- 待确认编号：`{command.command_id}`",
            f"- 决策结果：`{status}`",
        ]
        if default_skip:
            lines.append("- 默认策略：超时未确认，按不同步处理。")
        if completed_summary:
            writeback_counts = payload_dict(completed_summary.get("writeback_status_counts"))
            counts_text = (
                "，".join(f"{key} {writeback_counts[key]}" for key in sorted(writeback_counts))
                if writeback_counts
                else "暂无"
            )
            lines.extend(
                [
                    "",
                    "运行完成沉淀：",
                    f"- Run：`{payload_string(completed_summary.get('run_id')) or '未知'}` 已进入 `completed`",
                    f"- Batch：`{payload_string(completed_summary.get('batch_id')) or '未知'}`",
                    f"- Job 数：{int(completed_summary.get('job_count') or 0)}",
                    f"- 报告数：{int(completed_summary.get('report_count') or 0)}",
                    f"- 写回统计：{counts_text}",
                ]
            )
        lines.extend(["", "每行结果："])
        for row in row_results[:10]:
            lines.append(
                "- 行 `{row_id}` / `{case_id}` / `{job_id}`：`{status}`{error}".format(
                    row_id=payload_string(row.get("row_id")) or "未知行",
                    case_id=payload_string(row.get("case_id")) or "未知样本",
                    job_id=payload_string(row.get("job_id")) or "未知任务",
                    status=payload_string(row.get("writeback_status")) or "unknown",
                    error=(
                        f"（{_clip_text(payload_string(row.get('error_message')), 120)}）"
                        if payload_string(row.get("error_message"))
                        else ""
                    ),
                )
            )
        if len(row_results) > 10:
            lines.append(f"- 其余 {len(row_results) - 10} 行请在审计中查看。")
        return "\n".join(lines)

    def pending_command_action_reply(
        self,
        *,
        command: LarkBotPendingCommand,
        action_kind: str,
        markdown: str,
        content: dict[str, object] | None = None,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"card-action-{command.command_id}",
            action_kind=action_kind,
            status=command.status,
            target_type=self._reply_target_type(command),
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


def payload_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def payload_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def payload_string(value: object) -> str:
    return str(value).strip() if value is not None else ""

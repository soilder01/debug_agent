from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from debug_agent.jobs.service import SubmittedDebugJob
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.storage.repository import DebugJobRepository


class SpreadsheetWritebackClient(Protocol):
    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        """Persist fields to one spreadsheet row."""


class SpreadsheetWritebackResult(BaseModel):
    row_id: str
    fields: dict[str, str]


def build_report_writeback_fields(report: DebugReport, report_url: str) -> dict[str, str]:
    fields = dict(report.suggested_sheet_fields)
    recommended_actions = _recommended_actions(report)
    if recommended_actions:
        fields["推荐操作"] = recommended_actions
    fields["错误原因"] = fields.get("错误原因") or report.root_cause.label
    fields["评估问题反馈"] = _evaluation_feedback(report)
    fields["分析报告链接"] = report_url
    return fields


def write_report_to_spreadsheet_row(
    *,
    client: SpreadsheetWritebackClient,
    spreadsheet_id: str,
    sheet_id: str,
    row_id: str,
    report: DebugReport,
    report_url: str,
) -> SpreadsheetWritebackResult:
    fields = build_report_writeback_fields(report, report_url=report_url)
    client.update_row(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id, row_id=row_id, fields=fields)
    return SpreadsheetWritebackResult(row_id=row_id, fields=fields)


def write_report_for_job(
    *,
    repository: DebugJobRepository,
    client: SpreadsheetWritebackClient,
    job_id: str,
    report: DebugReport,
    report_url: str,
) -> SpreadsheetWritebackResult | None:
    mapping = repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is None:
        return None
    return write_report_to_spreadsheet_row(
        client=client,
        spreadsheet_id=mapping.spreadsheet_id,
        sheet_id=mapping.sheet_id,
        row_id=mapping.row_id,
        report=report,
        report_url=report_url,
    )


def make_spreadsheet_writeback_completion_hook(
    *,
    repository: DebugJobRepository,
    client: SpreadsheetWritebackClient,
    report_base_url: str,
) -> Callable[[SubmittedDebugJob], None]:
    base_url = report_base_url.rstrip("/")

    def on_job_completed(job: SubmittedDebugJob) -> None:
        if job.status != "completed":
            return
        report_url = f"{base_url}/jobs/{job.job_id}/report"
        report = build_report_for_job(repository, job.job_id)
        if report is None:
            repository.save_spreadsheet_writeback_audit(
                job_id=job.job_id,
                status="skipped",
                row_id="",
                report_url=report_url,
                fields={},
                error_message="debug report could not be rebuilt",
            )
            return
        mapping = repository.get_spreadsheet_row_mapping_by_job_id(job.job_id)
        if mapping is None:
            repository.save_spreadsheet_writeback_audit(
                job_id=job.job_id,
                status="skipped",
                row_id="",
                report_url=report_url,
                fields={},
                error_message="spreadsheet row mapping not found",
            )
            return
        try:
            result = write_report_to_spreadsheet_row(
                client=client,
                spreadsheet_id=mapping.spreadsheet_id,
                sheet_id=mapping.sheet_id,
                row_id=mapping.row_id,
                report=report,
                report_url=report_url,
            )
        except Exception as exc:
            repository.save_spreadsheet_writeback_audit(
                job_id=job.job_id,
                status="failed",
                row_id=mapping.row_id,
                report_url=report_url,
                fields={},
                error_message=str(exc),
            )
            raise
        repository.save_spreadsheet_writeback_audit(
            job_id=job.job_id,
            status="succeeded",
            row_id=result.row_id,
            report_url=report_url,
            fields=result.fields,
            error_message="",
        )

    return on_job_completed


def _evaluation_feedback(report: DebugReport) -> str:
    lines = [report.root_cause.evidence_summary]
    recommended_actions = _recommended_actions(report)
    if recommended_actions:
        lines.append(f"推荐操作：{recommended_actions}")
    verification_results = _verification_results(report)
    if verification_results:
        lines.append(f"推荐操作验证：{verification_results}")
    strategy_results = _strategy_follow_up_results(report)
    if strategy_results:
        lines.append(f"策略 Follow-up：{strategy_results}")
    if report.experiment_summary is not None:
        summary = report.experiment_summary
        lines.extend(
            [
                f"复测稳定性：{summary.stability_label}",
                f"复测通过率：{round(summary.success_rate * 100)}%",
                f"失败次数：{summary.failed_trial_count}/{summary.total_trials}",
            ]
        )
    return "\n".join(lines)


def _recommended_actions(report: DebugReport) -> str:
    return "\n".join(
        f"{action['category']}/{action['priority']}：{action['summary']} - {action['detail']}"
        for action in report.recommended_actions
    )


def _verification_results(report: DebugReport) -> str:
    return "\n".join(
        _verification_result_line(result)
        for result in report.verification_results
    )


def _verification_result_line(result: dict[str, object]) -> str:
    action_index = result.get("action_index")
    action_number = action_index + 1 if isinstance(action_index, int) else "未知"
    status = str(result.get("result", "unknown"))
    summary = str(result.get("summary", ""))
    return f"操作 {action_number}/{status}：{summary}"


def _strategy_follow_up_results(report: DebugReport) -> str:
    return "\n".join(
        _strategy_follow_up_result_line(result)
        for result in report.strategy_follow_up_results
    )


def _strategy_follow_up_result_line(result: dict[str, object]) -> str:
    stage = str(result.get("stage", "unknown"))
    outcome = str(result.get("outcome", "unknown"))
    summary = str(result.get("summary", ""))
    escalation = str(result.get("escalation", ""))
    line = f"{stage}/{outcome}：{summary}"
    if escalation:
        line = f"{line}\n升级：{escalation}"
    return line

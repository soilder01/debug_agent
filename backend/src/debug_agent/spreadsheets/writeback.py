from typing import Protocol

from pydantic import BaseModel

from debug_agent.reports.generator import DebugReport


class SpreadsheetWritebackClient(Protocol):
    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        """Persist fields to one spreadsheet row."""


class SpreadsheetWritebackResult(BaseModel):
    row_id: str
    fields: dict[str, str]


def build_report_writeback_fields(report: DebugReport, report_url: str) -> dict[str, str]:
    fields = dict(report.suggested_sheet_fields)
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


def _evaluation_feedback(report: DebugReport) -> str:
    lines = [report.root_cause.evidence_summary]
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

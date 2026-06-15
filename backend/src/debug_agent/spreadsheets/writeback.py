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
        target_job_ids = _writeback_target_job_ids(repository, job.job_id)
        for target_job_id in target_job_ids:
            _write_completed_job_report(
                repository=repository,
                client=client,
                job_id=target_job_id,
                report_url=f"{base_url}/jobs/{target_job_id}/report",
            )

    return on_job_completed


def _writeback_target_job_ids(repository: DebugJobRepository, completed_job_id: str) -> list[str]:
    sources = repository.list_strategy_follow_up_sources(completed_job_id)
    if sources:
        return [source.source_job_id for source in sources]
    targeted_sources = repository.list_targeted_probe_sources(completed_job_id)
    if targeted_sources:
        return [source.source_job_id for source in targeted_sources]
    return [completed_job_id]


def _write_completed_job_report(
    *,
    repository: DebugJobRepository,
    client: SpreadsheetWritebackClient,
    job_id: str,
    report_url: str,
) -> None:
    report = build_report_for_job(repository, job_id)
    if report is None:
        repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status="skipped",
            row_id="",
            report_url=report_url,
            fields={},
            error_message="debug report could not be rebuilt",
        )
        return
    mapping = repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is None:
        repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
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
            job_id=job_id,
            status="failed",
            row_id=mapping.row_id,
            report_url=report_url,
            fields={},
            error_message=str(exc),
        )
        raise
    repository.save_spreadsheet_writeback_audit(
        job_id=job_id,
        status="succeeded",
        row_id=result.row_id,
        report_url=report_url,
        fields=result.fields,
        error_message="",
    )


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
    targeted_results = _targeted_probe_results(report)
    if targeted_results:
        lines.append(f"Targeted Probe：{targeted_results}")
    targeted_guardrails = _targeted_probe_guardrails(report)
    if targeted_guardrails:
        lines.append(f"Targeted Guardrail：{targeted_guardrails}")
    human_handoffs = _human_handoff_requests(report)
    if human_handoffs:
        lines.append(f"人工接管：{human_handoffs}")
    human_handoff_statuses = _human_handoff_statuses(report)
    if human_handoff_statuses:
        lines.append(f"人工接管状态：{human_handoff_statuses}")
    final_attributions = _final_attributions(report)
    if final_attributions:
        lines.append(f"最终归因：{final_attributions}")
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


def _targeted_probe_results(report: DebugReport) -> str:
    return "\n".join(
        _targeted_probe_result_line(result)
        for result in report.targeted_probe_results
    )


def _targeted_probe_result_line(result: dict[str, object]) -> str:
    target_id = str(result.get("target_id", "unknown"))
    outcome = str(result.get("outcome", "unknown"))
    summary = str(result.get("summary", ""))
    escalation = str(result.get("escalation", ""))
    line = f"{target_id}/{outcome}：{summary}"
    if escalation:
        line = f"{line}\n升级：{escalation}"
    return line


def _targeted_probe_guardrails(report: DebugReport) -> str:
    return "\n".join(
        _targeted_probe_guardrail_line(follow_up)
        for follow_up in report.follow_up_experiments
        if follow_up.get("source") == "targeted_probe_guardrail"
    )


def _targeted_probe_guardrail_line(follow_up: dict[str, str]) -> str:
    target_id = follow_up.get("target_id", "unknown")
    result = follow_up.get("result", "unknown")
    summary = follow_up.get("summary", "")
    stop_condition = follow_up.get("stop_condition", "")
    line = f"{target_id}/{result}：{summary}"
    if stop_condition:
        line = f"{line}\n停止条件：{stop_condition}"
    return line


def _human_handoff_requests(report: DebugReport) -> str:
    return "\n".join(
        _human_handoff_line(request)
        for request in report.human_handoff_requests
    )


def _human_handoff_line(request: dict[str, str]) -> str:
    target_id = request.get("target_id", "unknown")
    priority = request.get("priority", "unknown")
    reason = request.get("reason", "unknown")
    owner = request.get("recommended_owner", "human-debugger")
    next_action = request.get("next_action", "")
    line = f"{target_id}/{priority}/{reason}"
    if owner:
        line = f"{line}\n负责人：{owner}"
    if next_action:
        line = f"{line}\n下一步：{next_action}"
    return line


def _human_handoff_statuses(report: DebugReport) -> str:
    return "\n".join(
        _human_handoff_status_line(status)
        for status in report.human_handoff_statuses
    )


def _human_handoff_status_line(status: dict[str, str]) -> str:
    target_id = status.get("target_id", "unknown")
    state = status.get("status", "unknown")
    actor = status.get("actor", "")
    note = status.get("note", "")
    line = f"{target_id}/{state}"
    if actor:
        line = f"{line}\n处理人：{actor}"
    if note:
        line = f"{line}\n结论：{note}"
    return line


def _final_attributions(report: DebugReport) -> str:
    return "\n".join(
        _final_attribution_line(attribution)
        for attribution in report.final_attributions
    )


def _final_attribution_line(attribution: dict[str, str]) -> str:
    target_id = attribution.get("target_id", "unknown")
    category = attribution.get("category", "unknown")
    status = attribution.get("status", "unknown")
    summary = attribution.get("summary", "")
    recommended_action = attribution.get("recommended_action", "")
    line = f"{target_id}/{category}/{status}：{summary}"
    if recommended_action:
        line = f"{line}\n建议：{recommended_action}"
    return line

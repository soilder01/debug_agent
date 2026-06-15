from typing import Literal

from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentRunResult
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.storage.repository import DebugJobRepository, RecommendedActionVerification


def build_report_for_job(repository: DebugJobRepository, job_id: str) -> DebugReport | None:
    base_report = _build_base_report_for_job(repository, job_id)
    if base_report is None:
        return None
    verification_results = build_recommended_action_verification_results(
        repository,
        job_id,
        source_report=base_report,
    )
    report = _build_base_report_for_job(repository, job_id, verification_results=verification_results)
    if report is None:
        return None
    return _merge_recommended_action_statuses(repository, job_id, report)


def _build_base_report_for_job(
    repository: DebugJobRepository,
    job_id: str,
    verification_results: list[dict[str, object]] | None = None,
) -> DebugReport | None:
    job = repository.get_job(job_id)
    if job is None:
        return None
    case = repository.get_case(job.case_id)
    if case is None:
        return None
    evidence = repository.list_evidence(job_id)
    plan = plan_experiments(case, baseline_trials=job.baseline_trials or None)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=sum(1 for item in evidence if item.judge.score == 1),
        evidence=evidence,
    )
    return generate_initial_report(
        case=case,
        plan=plan,
        run_result=run_result,
        job_id=job_id,
        verification_results=verification_results,
    )


def build_recommended_action_verification_results(
    repository: DebugJobRepository,
    job_id: str,
    source_report: DebugReport | None = None,
) -> list[dict[str, object]]:
    resolved_source_report = source_report or _build_base_report_for_job(repository, job_id)
    return [
        _recommended_action_verification_result(
            repository=repository,
            job_id=job_id,
            verification=verification,
            source_report=resolved_source_report,
        )
        for verification in repository.list_recommended_action_verifications(job_id)
    ]


def _recommended_action_verification_result(
    *,
    repository: DebugJobRepository,
    job_id: str,
    verification: RecommendedActionVerification,
    source_report: DebugReport | None,
) -> dict[str, object]:
    source_success_rate = _report_success_rate(source_report)
    source_root_cause = source_report.root_cause.label if source_report is not None else ""
    verification_job = repository.get_job(verification.verification_job_id)
    if verification_job is None or verification_job.status != "completed":
        return {
            "job_id": job_id,
            "action_index": verification.action_index,
            "verification_job_id": verification.verification_job_id,
            "result": "pending",
            "source_success_rate": source_success_rate,
            "verification_success_rate": 0.0,
            "source_root_cause": source_root_cause,
            "verification_root_cause": "",
            "summary": "验证任务尚未完成，等待复测结果后再判断推荐操作是否生效。",
        }
    verification_report = _build_base_report_for_job(repository, verification.verification_job_id)
    verification_success_rate = _report_success_rate(verification_report)
    verification_root_cause = verification_report.root_cause.label if verification_report is not None else ""
    result = _classify_verification_result(
        source_success_rate=source_success_rate,
        verification_success_rate=verification_success_rate,
        has_verification_report=verification_report is not None,
    )
    return {
        "job_id": job_id,
        "action_index": verification.action_index,
        "verification_job_id": verification.verification_job_id,
        "result": result,
        "source_success_rate": source_success_rate,
        "verification_success_rate": verification_success_rate,
        "source_root_cause": source_root_cause,
        "verification_root_cause": verification_root_cause,
        "summary": _verification_result_summary(
            result=result,
            source_success_rate=source_success_rate,
            verification_success_rate=verification_success_rate,
        ),
    }


def _report_success_rate(report: DebugReport | None) -> float:
    if report is None or report.experiment_summary is None:
        return 0.0
    return report.experiment_summary.success_rate


def _classify_verification_result(
    *,
    source_success_rate: float,
    verification_success_rate: float,
    has_verification_report: bool,
) -> Literal["resolved", "not_resolved", "regressed", "inconclusive"]:
    if not has_verification_report:
        return "inconclusive"
    if verification_success_rate < source_success_rate:
        return "regressed"
    if verification_success_rate >= 1.0 and verification_success_rate > source_success_rate:
        return "resolved"
    if verification_success_rate <= source_success_rate:
        return "not_resolved"
    return "inconclusive"


def _verification_result_summary(
    *,
    result: str,
    source_success_rate: float,
    verification_success_rate: float,
) -> str:
    source_percent = round(source_success_rate * 100)
    verification_percent = round(verification_success_rate * 100)
    if result == "resolved":
        return f"验证任务通过率 {verification_percent}%，高于原任务 {source_percent}%，推荐操作可能已修复该问题。"
    if result == "regressed":
        return f"验证任务通过率 {verification_percent}%，低于原任务 {source_percent}%，推荐操作可能引入回归。"
    if result == "not_resolved":
        return f"验证任务通过率 {verification_percent}%，未高于原任务 {source_percent}%，推荐操作尚未证明有效。"
    return "验证任务结果不足以判断推荐操作是否生效。"


def _merge_recommended_action_statuses(
    repository: DebugJobRepository,
    job_id: str,
    report: DebugReport,
) -> DebugReport:
    statuses = {
        item.action_index: item.status
        for item in repository.list_recommended_action_statuses(job_id)
    }
    if not statuses or not report.recommended_actions:
        return report
    report.recommended_actions = [
        {**action, "status": statuses.get(index, action.get("status", "pending"))}
        for index, action in enumerate(report.recommended_actions)
    ]
    return report

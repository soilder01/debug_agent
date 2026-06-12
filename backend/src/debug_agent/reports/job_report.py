from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentRunResult
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.storage.repository import DebugJobRepository


def build_report_for_job(repository: DebugJobRepository, job_id: str) -> DebugReport | None:
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
    return generate_initial_report(case=case, plan=plan, run_result=run_result, job_id=job_id)

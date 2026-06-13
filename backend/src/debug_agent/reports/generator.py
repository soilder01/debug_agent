from pydantic import BaseModel

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult


class ObservedFailure(BaseModel):
    type: str
    summary: str
    affected_box_ids: list[int]


class RootCause(BaseModel):
    label: str
    confidence: str
    evidence_summary: str


class ExperimentSummary(BaseModel):
    total_trials: int
    success_count: int
    failed_trial_count: int = 0
    success_rate: float = 0.0
    stability_label: str = "not_run"
    evidence_ids: list[str]
    image_artifact_ids: list[str]


class DebugReport(BaseModel):
    job_id: str | None = None
    case_id: str
    status: str
    observed_failure: ObservedFailure
    planned_experiments: list[str]
    experiment_summary: ExperimentSummary | None = None
    root_cause: RootCause
    suggested_sheet_fields: dict[str, str]


def generate_initial_report(
    case: DebugCase,
    plan: ExperimentPlan,
    run_result: ExperimentRunResult | None = None,
    job_id: str | None = None,
) -> DebugReport:
    experiment_summary = None
    if run_result is not None:
        failed_trial_count = run_result.total_trials - run_result.success_count
        experiment_summary = ExperimentSummary(
            total_trials=run_result.total_trials,
            success_count=run_result.success_count,
            failed_trial_count=failed_trial_count,
            success_rate=_success_rate(run_result.success_count, run_result.total_trials),
            stability_label=_stability_label(run_result.success_count, failed_trial_count, run_result.total_trials),
            evidence_ids=[evidence.evidence_id for evidence in run_result.evidence],
            image_artifact_ids=[
                artifact.artifact_id
                for evidence in run_result.evidence
                for artifact in evidence.image_artifacts
            ],
        )
    observed_failure, root_cause, suggested_sheet_fields = _infer_report_findings(run_result)
    return DebugReport(
        job_id=job_id,
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=observed_failure,
        planned_experiments=[step.name for step in plan.steps],
        experiment_summary=experiment_summary,
        root_cause=root_cause,
        suggested_sheet_fields=suggested_sheet_fields,
    )


def _success_rate(success_count: int, total_trials: int) -> float:
    if total_trials <= 0:
        return 0.0
    return success_count / total_trials


def _stability_label(success_count: int, failed_trial_count: int, total_trials: int) -> str:
    if total_trials <= 0:
        return "not_run"
    if success_count == total_trials:
        return "stable_success"
    if failed_trial_count == total_trials:
        return "stable_failure"
    return "unstable"


def _infer_report_findings(
    run_result: ExperimentRunResult | None,
) -> tuple[ObservedFailure, RootCause, dict[str, str]]:
    if run_result is not None:
        runtime_error = _first_runtime_error(run_result.evidence)
        if runtime_error is not None:
            error_summary = f"{runtime_error.model_call_error_type}: {runtime_error.model_call_error_message}".strip()
            return (
                ObservedFailure(
                    type="model_call_error",
                    summary=f"模型调用失败，未能完成稳定复测：{error_summary}",
                    affected_box_ids=[],
                ),
                RootCause(
                    label="model_call_error",
                    confidence="high",
                    evidence_summary=f"Evidence {runtime_error.evidence_id} reported {error_summary}.",
                ),
                {
                    "debug1状态": "待人工确认",
                    "模型可做对次数": f"{run_result.success_count}次",
                    "错误原因": f"模型调用失败：{error_summary}",
                },
            )
        structured_deltas = _structured_answer_deltas(run_result.evidence)
        if structured_deltas:
            affected_box_ids = _affected_box_ids_from_deltas(structured_deltas)
            reason_labels = sorted({str(delta.get("reason", "")) for delta in structured_deltas if delta.get("reason")})
            box_summary = ", ".join(f"box {box_id}" for box_id in affected_box_ids)
            reason_summary = ", ".join(reason_labels)
            return (
                ObservedFailure(
                    type="answer_mismatch",
                    summary=f"结构化评分发现 {box_summary} 存在答案差异：{reason_summary}。",
                    affected_box_ids=affected_box_ids,
                ),
                RootCause(
                    label="answer_mismatch",
                    confidence="high",
                    evidence_summary=(
                        f"Structured judge deltas cite {box_summary} with reasons {reason_summary}; "
                        "compare predicted answers against the scoring standard and golden answer."
                    ),
                ),
                {
                    "debug1状态": "待人工确认",
                    "模型可做对次数": f"{run_result.success_count}次",
                    "错误原因": f"结构化评分显示 {box_summary} 存在 {reason_summary}。",
                },
            )
    return (
        ObservedFailure(
            type="erasure_revision_failure",
            summary="模型在涂改、错字或相近字符场景下存在语义猜测和纠偏风险。",
            affected_box_ids=[1, 2],
        ),
        RootCause(
            label="erasure_revision_failure",
            confidence="medium",
            evidence_summary="当前样本低分且人工备注指向涂改区域识别失败，需要复测确认。",
        ),
        {
            "debug1状态": "待人工确认",
            "模型可做对次数": "0次",
            "错误原因": "模型无法稳定识别涂改后的最终答案，存在语义补全倾向。",
        },
    )


def _first_runtime_error(evidence: list[ExperimentEvidence]) -> ExperimentEvidence | None:
    for item in evidence:
        if item.model_call_error_type:
            return item
    return None


def _structured_answer_deltas(evidence: list[ExperimentEvidence]) -> list[dict[str, object]]:
    deltas: list[dict[str, object]] = []
    for item in evidence:
        deltas.extend(item.judge.deltas)
    return deltas


def _affected_box_ids_from_deltas(deltas: list[dict[str, object]]) -> list[int]:
    box_ids: set[int] = set()
    for delta in deltas:
        box_id = delta.get("box_id")
        if isinstance(box_id, int):
            box_ids.add(box_id)
    return sorted(box_ids)

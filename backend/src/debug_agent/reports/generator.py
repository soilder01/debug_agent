from pydantic import BaseModel

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.experiments.runner import ExperimentRunResult


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
    evidence_ids: list[str]


class DebugReport(BaseModel):
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
) -> DebugReport:
    experiment_summary = None
    if run_result is not None:
        experiment_summary = ExperimentSummary(
            total_trials=run_result.total_trials,
            success_count=run_result.success_count,
            evidence_ids=[evidence.evidence_id for evidence in run_result.evidence],
        )
    return DebugReport(
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="erasure_revision_failure",
            summary="模型在涂改、错字或相近字符场景下存在语义猜测和纠偏风险。",
            affected_box_ids=[1, 2],
        ),
        planned_experiments=[step.name for step in plan.steps],
        experiment_summary=experiment_summary,
        root_cause=RootCause(
            label="erasure_revision_failure",
            confidence="medium",
            evidence_summary="当前样本低分且人工备注指向涂改区域识别失败，需要复测确认。",
        ),
        suggested_sheet_fields={
            "debug1状态": "待人工确认",
            "模型可做对次数": "0次",
            "错误原因": "模型无法稳定识别涂改后的最终答案，存在语义补全倾向。",
        },
    )

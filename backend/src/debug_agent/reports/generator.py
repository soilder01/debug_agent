from pydantic import BaseModel

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan


class ObservedFailure(BaseModel):
    type: str
    summary: str
    affected_box_ids: list[int]


class RootCause(BaseModel):
    label: str
    confidence: str
    evidence_summary: str


class DebugReport(BaseModel):
    case_id: str
    status: str
    observed_failure: ObservedFailure
    planned_experiments: list[str]
    root_cause: RootCause
    suggested_sheet_fields: dict[str, str]


def generate_initial_report(case: DebugCase, plan: ExperimentPlan) -> DebugReport:
    return DebugReport(
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="erasure_revision_failure",
            summary="模型在涂改、错字或相近字符场景下存在语义猜测和纠偏风险。",
            affected_box_ids=[1, 2],
        ),
        planned_experiments=[step.name for step in plan.steps],
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

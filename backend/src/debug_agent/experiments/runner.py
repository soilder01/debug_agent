from pydantic import BaseModel

from debug_agent.cases.comparator import parse_prediction_answer
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.judging.runner import JudgeResult, judge_answer
from debug_agent.models.adapters import ModelAdapter


class ExperimentEvidence(BaseModel):
    evidence_id: str
    step_name: str
    trial: int
    model_name: str = ""
    model_provider: str = ""
    model_id: str = ""
    raw_output: str
    judge: JudgeResult


class ExperimentRunResult(BaseModel):
    case_id: str
    total_trials: int
    success_count: int
    evidence: list[ExperimentEvidence]


async def run_experiments(
    case: DebugCase,
    plan: ExperimentPlan,
    adapter: ModelAdapter,
) -> ExperimentRunResult:
    evidence: list[ExperimentEvidence] = []
    success_count = 0
    for step in plan.steps:
        for trial_index in range(step.trials):
            response = await adapter.generate(prompt=case.prompt, image_uri=case.image_uri)
            predicted = parse_prediction_answer(response.raw_output)
            judge = judge_answer(case.golden_answer, predicted)
            success_count += judge.score
            evidence.append(
                ExperimentEvidence(
                    evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                    step_name=step.name,
                    trial=trial_index,
                    model_name=response.model_name,
                    model_provider=response.model_provider,
                    model_id=response.model_id,
                    raw_output=response.raw_output,
                    judge=judge,
                )
            )
    return ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=success_count,
        evidence=evidence,
    )

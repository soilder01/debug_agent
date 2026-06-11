from pydantic import BaseModel

from debug_agent.cases.models import DebugCase


class ExperimentStep(BaseModel):
    name: str
    description: str
    trials: int


class ExperimentPlan(BaseModel):
    case_id: str
    max_model_calls: int
    steps: list[ExperimentStep]


def plan_experiments(case: DebugCase, baseline_trials: int | None = None) -> ExperimentPlan:
    resolved_baseline_trials = baseline_trials if baseline_trials is not None else min(5, max(1, len(case.predictions)))
    steps = [
        ExperimentStep(
            name="baseline_replay",
            description="Replay the original prompt and image condition to confirm the failure.",
            trials=resolved_baseline_trials,
        ),
        ExperimentStep(
            name="strict_prompt_replay",
            description="Replay with stronger instruction to avoid semantic correction and guessing.",
            trials=3,
        ),
        ExperimentStep(
            name="localized_observation_request",
            description="Ask the model to describe the affected answer region before extracting final JSON.",
            trials=2,
        ),
    ]
    return ExperimentPlan(case_id=case.case_id, max_model_calls=10, steps=steps)

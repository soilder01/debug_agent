from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase


class AblationVariant(BaseModel):
    name: str
    modalities: list[str] = Field(default_factory=list)
    prompt_instructions: str = ""
    image_uri: str | None = None


class ExperimentStep(BaseModel):
    name: str
    description: str
    trials: int
    ablation_variants: list[AblationVariant] = Field(default_factory=list)


class ExperimentPlan(BaseModel):
    case_id: str
    max_model_calls: int
    steps: list[ExperimentStep]


def plan_experiments(case: DebugCase, baseline_trials: int | None = None) -> ExperimentPlan:
    from debug_agent.recipes import recipe_for_task_type

    resolved_baseline_trials = baseline_trials if baseline_trials is not None else min(5, max(1, len(case.predictions)))
    recipe = recipe_for_task_type(case.task_type)
    steps = recipe.plan_steps(case=case, baseline_trials=resolved_baseline_trials)
    return ExperimentPlan(case_id=case.case_id, max_model_calls=10, steps=steps)


def plan_verification_follow_up_experiments(
    case: DebugCase,
    verification_result: dict[str, object],
    baseline_trials: int | None = None,
) -> ExperimentPlan:
    base_plan = plan_experiments(case, baseline_trials=baseline_trials)
    result = verification_result.get("result")
    verification_job_id = verification_result.get("verification_job_id")
    if result not in {"not_resolved", "regressed"} or not isinstance(verification_job_id, str):
        return base_plan

    probe_name = "verification_regression_probe" if result == "regressed" else "verification_unresolved_probe"
    probe_label = "regressed" if result == "regressed" else "unresolved"
    return ExperimentPlan(
        case_id=base_plan.case_id,
        max_model_calls=base_plan.max_model_calls,
        steps=[
            *base_plan.steps,
            ExperimentStep(
                name=probe_name,
                description=f"Probe {probe_label} verification job {verification_job_id} with a targeted follow-up experiment.",
                trials=1,
            ),
        ],
    )

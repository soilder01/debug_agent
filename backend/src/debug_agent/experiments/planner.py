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


def plan_strategy_follow_up_experiments(
    case: DebugCase,
    debug_strategy: list[dict[str, str]],
    baseline_trials: int | None = None,
) -> ExperimentPlan:
    base_plan = plan_experiments(case, baseline_trials=baseline_trials)
    strategy_steps = [
        ExperimentStep(
            name=f"strategy_{_safe_strategy_stage(stage)}_probe",
            description=f"Run strategy stage {stage}: {planned_probe}",
            trials=1,
        )
        for item in debug_strategy
        if (stage := item.get("stage"))
        and isinstance(stage, str)
        and stage.strip()
        and (planned_probe := item.get("planned_probe"))
        and isinstance(planned_probe, str)
        and planned_probe.strip()
    ]
    if not strategy_steps:
        return base_plan
    return ExperimentPlan(
        case_id=base_plan.case_id,
        max_model_calls=base_plan.max_model_calls,
        steps=[*base_plan.steps, *strategy_steps],
    )


def plan_strategy_escalation_follow_up_experiments(
    case: DebugCase,
    strategy_follow_up_results: list[dict[str, object]],
    baseline_trials: int | None = None,
) -> ExperimentPlan:
    base_plan = plan_experiments(case, baseline_trials=baseline_trials)
    escalation_steps = [
        ExperimentStep(
            name=_strategy_escalation_probe_name(stage),
            description=f"Escalate strategy stage {stage} from follow-up job {follow_up_job_id}: {escalation}",
            trials=1,
        )
        for item in strategy_follow_up_results
        if item.get("outcome") == "needs_escalation"
        and (stage := item.get("stage"))
        and isinstance(stage, str)
        and (follow_up_job_id := item.get("follow_up_job_id"))
        and isinstance(follow_up_job_id, str)
        and (escalation := item.get("escalation"))
        and isinstance(escalation, str)
        and escalation.strip()
    ]
    if not escalation_steps:
        return base_plan
    return ExperimentPlan(
        case_id=base_plan.case_id,
        max_model_calls=base_plan.max_model_calls,
        steps=[*base_plan.steps, *escalation_steps],
    )


def plan_targeted_probe_experiments(
    case: DebugCase,
    root_cause_trace: list[dict[str, object]],
    baseline_trials: int | None = None,
) -> ExperimentPlan:
    base_plan = plan_experiments(case, baseline_trials=baseline_trials)
    target_ids = _target_ids_from_trace(root_cause_trace)
    targeted_steps = [
        step
        for target_id in target_ids
        if (step := _targeted_probe_step(target_id)) is not None
    ]
    if not targeted_steps:
        return base_plan
    return ExperimentPlan(
        case_id=base_plan.case_id,
        max_model_calls=base_plan.max_model_calls,
        steps=[*base_plan.steps, *targeted_steps],
    )


def plan_targeted_escalation_follow_up_experiments(
    case: DebugCase,
    targeted_probe_results: list[dict[str, object]],
    baseline_trials: int | None = None,
) -> ExperimentPlan:
    base_plan = plan_experiments(case, baseline_trials=baseline_trials)
    escalation_steps = [
        ExperimentStep(
            name=_targeted_escalation_probe_name(target_id),
            description=f"Escalate targeted probe {target_id} from probe job {probe_job_id}: {escalation}",
            trials=1,
        )
        for item in targeted_probe_results
        if item.get("outcome") in {"target_still_failing", "inconclusive"}
        and (target_id := item.get("target_id"))
        and isinstance(target_id, str)
        and (probe_job_id := item.get("probe_job_id"))
        and isinstance(probe_job_id, str)
        and (escalation := item.get("escalation"))
        and isinstance(escalation, str)
        and escalation.strip()
    ]
    if not escalation_steps:
        return base_plan
    return ExperimentPlan(
        case_id=base_plan.case_id,
        max_model_calls=base_plan.max_model_calls,
        steps=[*base_plan.steps, *escalation_steps],
    )


def _target_ids_from_trace(root_cause_trace: list[dict[str, object]]) -> list[str]:
    target_ids: list[str] = []
    for trace in root_cause_trace:
        values = trace.get("target_ids")
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value and value not in target_ids:
                target_ids.append(value)
    return target_ids


def _targeted_probe_step(target_id: str) -> ExperimentStep | None:
    if target_id.startswith("image:region:"):
        return ExperimentStep(
            name="targeted_image_region_probe",
            description=f"Probe image region target {target_id} with localized evidence replay.",
            trials=1,
        )
    if target_id.startswith("video:segment:"):
        return ExperimentStep(
            name="targeted_video_segment_probe",
            description=f"Probe video segment target {target_id} with temporal evidence replay.",
            trials=1,
        )
    if target_id.startswith("multimodal:conflict:"):
        return ExperimentStep(
            name="targeted_multimodal_conflict_probe",
            description=f"Probe multimodal conflict target {target_id} with cross-modal evidence replay.",
            trials=1,
        )
    return None


def _strategy_escalation_probe_name(stage: str) -> str:
    if stage == "ablation_expansion":
        return "strategy_escalation_single_modality_probe"
    return f"strategy_escalation_{_safe_strategy_stage(stage)}_probe"


def _targeted_escalation_probe_name(target_id: str) -> str:
    if target_id.startswith("image:region:"):
        return "targeted_escalation_image_region_probe"
    if target_id.startswith("video:segment:"):
        return "targeted_escalation_video_segment_probe"
    if target_id.startswith("multimodal:conflict:"):
        return "targeted_escalation_multimodal_conflict_probe"
    return "targeted_escalation_probe"


def _safe_strategy_stage(stage: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in stage.strip().lower()).strip("_")

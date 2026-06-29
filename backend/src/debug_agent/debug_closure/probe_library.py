from __future__ import annotations

from pydantic import BaseModel, Field

from debug_agent.debug_closure.hypotheses import HypothesisCategory, ProbeInterventionType


MODEL_RUNNER_INTERVENTIONS: frozenset[ProbeInterventionType] = frozenset(
    {
        "prompt_patch",
        "stability_rerun",
        "input_localization",
        "schema_constraint",
    }
)


class ProbeStrategy(BaseModel):
    category: HypothesisCategory
    default_intervention: ProbeInterventionType
    allowed_interventions: list[ProbeInterventionType] = Field(default_factory=list)
    requires_locked_model_runner: bool = False
    description: str

    def allows(self, intervention_type: ProbeInterventionType) -> bool:
        return intervention_type in self.allowed_interventions


PROBE_STRATEGIES: tuple[ProbeStrategy, ...] = (
    ProbeStrategy(
        category="prompt_constraint",
        default_intervention="prompt_patch",
        allowed_interventions=["prompt_patch", "schema_constraint"],
        requires_locked_model_runner=True,
        description="Patch only the prompt constraints and rerun with the locked source model.",
    ),
    ProbeStrategy(
        category="scoring_strictness",
        default_intervention="scoring_variant",
        allowed_interventions=["scoring_variant", "judge_crosscheck"],
        description="Rescore existing outputs with bounded rubric variants before rerunning.",
    ),
    ProbeStrategy(
        category="golden_answer_ambiguity",
        default_intervention="golden_equivalence",
        allowed_interventions=["golden_equivalence", "judge_crosscheck"],
        description="Compare whether reference answer wording is semantically ambiguous.",
    ),
    ProbeStrategy(
        category="model_stability",
        default_intervention="stability_rerun",
        allowed_interventions=["stability_rerun"],
        requires_locked_model_runner=True,
        description="Repeat the original prompt with the locked source model to measure output variance.",
    ),
    ProbeStrategy(
        category="input_evidence",
        default_intervention="input_localization",
        allowed_interventions=["input_localization"],
        requires_locked_model_runner=True,
        description="Localize the input evidence while preserving the locked source model.",
    ),
    ProbeStrategy(
        category="schema_constraint",
        default_intervention="schema_constraint",
        allowed_interventions=["schema_constraint", "prompt_patch"],
        requires_locked_model_runner=True,
        description="Add bounded schema/checklist constraints and rerun with the locked source model.",
    ),
    ProbeStrategy(
        category="judge_disagreement",
        default_intervention="judge_crosscheck",
        allowed_interventions=["judge_crosscheck", "scoring_variant"],
        description="Cross-check judge reasoning without replacing deterministic scoring.",
    ),
    ProbeStrategy(
        category="media_resolution",
        default_intervention="input_localization",
        allowed_interventions=["input_localization", "stability_rerun"],
        requires_locked_model_runner=True,
        description="Verify media resolution and localized evidence with the locked source model.",
    ),
)


def strategy_for_category(category: HypothesisCategory) -> ProbeStrategy:
    return next(strategy for strategy in PROBE_STRATEGIES if strategy.category == category)


def intervention_requires_locked_model_runner(intervention_type: ProbeInterventionType) -> bool:
    return intervention_type in MODEL_RUNNER_INTERVENTIONS

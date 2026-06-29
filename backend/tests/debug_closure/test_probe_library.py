import pytest

from debug_agent.debug_closure.hypotheses import HypothesisCategory
from debug_agent.debug_closure.probe_library import (
    PROBE_STRATEGIES,
    intervention_requires_locked_model_runner,
    strategy_for_category,
)


def test_probe_library_covers_all_hypothesis_categories() -> None:
    expected_categories = set(HypothesisCategory.__args__)  # type: ignore[attr-defined]

    assert {strategy.category for strategy in PROBE_STRATEGIES} == expected_categories


@pytest.mark.parametrize(
    ("category", "default_intervention", "requires_locked_runner"),
    [
        ("prompt_constraint", "prompt_patch", True),
        ("scoring_strictness", "scoring_variant", False),
        ("golden_answer_ambiguity", "golden_equivalence", False),
        ("model_stability", "stability_rerun", True),
        ("input_evidence", "input_localization", True),
        ("schema_constraint", "schema_constraint", True),
        ("judge_disagreement", "judge_crosscheck", False),
        ("media_resolution", "input_localization", True),
    ],
)
def test_probe_library_declares_default_interventions(
    category: HypothesisCategory,
    default_intervention: str,
    requires_locked_runner: bool,
) -> None:
    strategy = strategy_for_category(category)

    assert strategy.default_intervention == default_intervention
    assert strategy.requires_locked_model_runner is requires_locked_runner
    assert strategy.allows(strategy.default_intervention)


def test_model_runner_interventions_are_explicitly_locked() -> None:
    assert intervention_requires_locked_model_runner("prompt_patch")
    assert intervention_requires_locked_model_runner("stability_rerun")
    assert intervention_requires_locked_model_runner("input_localization")
    assert intervention_requires_locked_model_runner("schema_constraint")
    assert not intervention_requires_locked_model_runner("scoring_variant")
    assert not intervention_requires_locked_model_runner("golden_equivalence")
    assert not intervention_requires_locked_model_runner("judge_crosscheck")

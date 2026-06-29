from debug_agent.debug_closure.hypotheses import DebugHypothesis
from debug_agent.debug_closure.probe_synthesizer import synthesize_probe_plans


def test_synthesize_probe_plans_builds_jszn_096_style_hypothesis_matrix() -> None:
    hypotheses = [
        DebugHypothesis(
            hypothesis_id="h-prompt",
            category="prompt_constraint",
            claim="Prompt does not force right-arm and both-arm details.",
            supporting_evidence_ids=["e-baseline"],
            missing_evidence=["prompt patch rerun"],
            confidence_before_probe="medium",
        ),
        DebugHypothesis(
            hypothesis_id="h-scoring",
            category="scoring_strictness",
            claim="Strict rubric may be over-penalizing semantically close output.",
            supporting_evidence_ids=["e-judge"],
            missing_evidence=["lenient rescore"],
            confidence_before_probe="medium",
        ),
        DebugHypothesis(
            hypothesis_id="h-stability",
            category="model_stability",
            claim="The model may randomly omit required limb details.",
            supporting_evidence_ids=["e-repeat"],
            missing_evidence=["same prompt reruns"],
            confidence_before_probe="low",
        ),
        DebugHypothesis(
            hypothesis_id="h-golden",
            category="golden_answer_ambiguity",
            claim="Reference answer may be narrower than acceptable semantic action.",
            supporting_evidence_ids=["e-reference"],
            missing_evidence=["semantic equivalence note"],
            confidence_before_probe="low",
        ),
    ]

    plans = synthesize_probe_plans(hypotheses, default_model_runner_trials=5)

    by_hypothesis = {plan.hypothesis_id: plan for plan in plans}
    assert by_hypothesis["h-prompt"].intervention_type == "prompt_patch"
    assert by_hypothesis["h-prompt"].trials == 5
    assert by_hypothesis["h-prompt"].model_runner_config_ref == "locked_source"
    assert by_hypothesis["h-prompt"].intervention_payload["forbidden_changes"] == [
        "model_id",
        "mode",
        "thinking",
        "media_uri",
        "scoring_standard",
    ]
    assert by_hypothesis["h-scoring"].intervention_type == "scoring_variant"
    assert by_hypothesis["h-scoring"].trials == 1
    assert by_hypothesis["h-stability"].intervention_type == "stability_rerun"
    assert (
        by_hypothesis["h-stability"].success_criteria["must_preserve_locked_model_runner"] is True
    )
    assert by_hypothesis["h-golden"].intervention_type == "golden_equivalence"
    assert (
        by_hypothesis["h-golden"].success_criteria["does_not_override_deterministic_score"] is True
    )


def test_synthesize_probe_plans_deduplicates_probe_ids() -> None:
    hypotheses = [
        DebugHypothesis(
            hypothesis_id="h-duplicate",
            category="input_evidence",
            claim="Need localized evidence.",
        ),
        DebugHypothesis(
            hypothesis_id="h-duplicate",
            category="schema_constraint",
            claim="Duplicate should not produce a second plan.",
        ),
    ]

    plans = synthesize_probe_plans(hypotheses)

    assert [plan.probe_id for plan in plans] == ["probe-h-duplicate"]
    assert plans[0].intervention_type == "input_localization"

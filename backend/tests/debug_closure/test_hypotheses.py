import pytest
from pydantic import ValidationError

from debug_agent.debug_closure.hypotheses import (
    CausalComparisonResult,
    DebugHypothesis,
    DebugProbePlan,
    HypothesisClosurePayload,
    normalize_hypotheses,
)


def test_debug_hypothesis_requires_supported_category_and_text() -> None:
    hypothesis = DebugHypothesis(
        hypothesis_id="h-prompt",
        category="prompt_constraint",
        claim="Prompt does not force right-arm and both-arm details.",
        supporting_evidence_ids=["e1", "e1", " "],
        missing_evidence=["prompt patch rerun", "prompt patch rerun"],
        confidence_before_probe="high",
    )

    assert hypothesis.supporting_evidence_ids == ["e1"]
    assert hypothesis.missing_evidence == ["prompt patch rerun"]

    with pytest.raises(ValidationError):
        DebugHypothesis(
            hypothesis_id=" ",
            category="prompt_constraint",
            claim="missing id",
        )


def test_probe_plan_locks_model_runner_config_ref() -> None:
    plan = DebugProbePlan(
        probe_id="probe-prompt",
        hypothesis_id="h-prompt",
        intervention_type="prompt_patch",
        intervention_payload={"prompt_patch": "ask for right arm"},
        trials=5,
        success_criteria={"must_include": ["右臂", "双臂配合"]},
        stop_condition="stop after 5 locked-source trials",
    )

    assert plan.model_runner_config_ref == "locked_source"
    assert plan.trials == 5

    with pytest.raises(ValidationError):
        DebugProbePlan(
            probe_id="probe-too-many",
            hypothesis_id="h-prompt",
            intervention_type="stability_rerun",
            trials=100,
            stop_condition="bounded",
        )


def test_normalize_hypotheses_keeps_agent_output_candidate_until_probe_supports_it() -> None:
    hypotheses = normalize_hypotheses(
        [
            DebugHypothesis(
                hypothesis_id="h-agent-overclaim",
                category="model_stability",
                claim="Model is unstable.",
                supporting_evidence_ids=[],
                confidence_before_probe="high",
                status="supported",
            ),
            DebugHypothesis(
                hypothesis_id="h-agent-overclaim",
                category="model_stability",
                claim="duplicate should be ignored.",
            ),
        ]
    )

    assert len(hypotheses) == 1
    assert hypotheses[0].status == "candidate"
    assert hypotheses[0].confidence_before_probe == "low"


def test_causal_comparison_and_payload_are_serializable_for_stage_output() -> None:
    payload = HypothesisClosurePayload(
        hypotheses=[
            DebugHypothesis(
                hypothesis_id="h-scoring",
                category="scoring_strictness",
                claim="Strict rubric requires keywords missing from semantically close output.",
                supporting_evidence_ids=["e1"],
                confidence_before_probe="medium",
            )
        ],
        probe_plans=[
            DebugProbePlan(
                probe_id="probe-scoring",
                hypothesis_id="h-scoring",
                intervention_type="scoring_variant",
                intervention_payload={"variant": "lenient"},
                trials=1,
                success_criteria={"lenient_score_gt": 0},
                stop_condition="single deterministic rescore",
            )
        ],
        causal_comparisons=[
            CausalComparisonResult(
                hypothesis_id="h-scoring",
                probe_id="probe-scoring",
                baseline_success_rate=0.0,
                intervention_success_rate=0.5,
                delta=0.5,
                verdict="supported",
                evidence_summary="Lenient rubric partially passes existing output.",
            )
        ],
        fairness_lock={"model_runner_config_ref": "locked_source"},
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["hypotheses"][0]["status"] == "candidate"
    assert dumped["probe_plans"][0]["model_runner_config_ref"] == "locked_source"
    assert dumped["causal_comparisons"][0]["verdict"] == "supported"

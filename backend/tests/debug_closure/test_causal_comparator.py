from debug_agent.debug_closure.causal_comparator import compare_probe_outcome
from debug_agent.debug_closure.hypotheses import DebugProbePlan


def test_causal_comparator_supports_prompt_constraint_when_intervention_improves() -> None:
    result = compare_probe_outcome(
        plan=_plan("prompt_patch"),
        baseline_success_rate=0.0,
        intervention_success_rate=0.8,
        evidence_ids=["e-baseline", "e-probe"],
    )

    assert result.verdict == "supported"
    assert result.delta == 0.8
    assert "improved" in result.evidence_summary


def test_causal_comparator_rejects_prompt_constraint_without_lift() -> None:
    result = compare_probe_outcome(
        plan=_plan("prompt_patch"),
        baseline_success_rate=0.2,
        intervention_success_rate=0.2,
        evidence_ids=["e-baseline", "e-probe"],
    )

    assert result.verdict == "rejected"
    assert result.delta == 0.0


def test_causal_comparator_supports_model_stability_when_locked_reruns_vary() -> None:
    result = compare_probe_outcome(
        plan=_plan("stability_rerun"),
        baseline_success_rate=0.0,
        intervention_success_rate=0.4,
        evidence_ids=["e-rerun-1", "e-rerun-2"],
    )

    assert result.verdict == "supported"
    assert "variance" in result.evidence_summary


def test_causal_comparator_keeps_failed_probe_inconclusive() -> None:
    result = compare_probe_outcome(
        plan=_plan("prompt_patch"),
        baseline_success_rate=0.0,
        intervention_success_rate=0.0,
        evidence_ids=[],
        error_message="model timeout",
    )

    assert result.verdict == "inconclusive"
    assert "model timeout" in result.evidence_summary


def test_causal_comparator_does_not_promote_golden_equivalence_to_supported_root_cause() -> None:
    result = compare_probe_outcome(
        plan=_plan("golden_equivalence"),
        baseline_success_rate=0.0,
        intervention_success_rate=1.0,
        evidence_ids=["e-note"],
    )

    assert result.verdict == "inconclusive"
    assert "note-only" in result.evidence_summary


def _plan(intervention_type: str) -> DebugProbePlan:
    return DebugProbePlan(
        probe_id=f"probe-{intervention_type}",
        hypothesis_id=f"h-{intervention_type}",
        intervention_type=intervention_type,  # type: ignore[arg-type]
        intervention_payload={},
        trials=5,
        success_criteria={},
        stop_condition="bounded",
    )

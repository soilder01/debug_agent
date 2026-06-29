from __future__ import annotations

from debug_agent.debug_closure.hypotheses import DebugHypothesis, DebugProbePlan
from debug_agent.debug_closure.probe_library import strategy_for_category


DEFAULT_MODEL_RUNNER_TRIALS = 5


def synthesize_probe_plans(
    hypotheses: list[DebugHypothesis],
    *,
    default_model_runner_trials: int = DEFAULT_MODEL_RUNNER_TRIALS,
) -> list[DebugProbePlan]:
    plans: list[DebugProbePlan] = []
    seen: set[str] = set()
    for hypothesis in hypotheses:
        strategy = strategy_for_category(hypothesis.category)
        probe_id = f"probe-{hypothesis.hypothesis_id}"
        if probe_id in seen:
            continue
        seen.add(probe_id)
        trials = default_model_runner_trials if strategy.requires_locked_model_runner else 1
        plans.append(
            DebugProbePlan(
                probe_id=probe_id,
                hypothesis_id=hypothesis.hypothesis_id,
                intervention_type=strategy.default_intervention,
                iteration=hypothesis.iteration,
                intervention_payload=_intervention_payload(hypothesis),
                trials=trials,
                success_criteria=_success_criteria(hypothesis),
                stop_condition=_stop_condition(
                    strategy.requires_locked_model_runner,
                    trials=trials,
                ),
            )
        )
    return plans


def _intervention_payload(hypothesis: DebugHypothesis) -> dict[str, object]:
    base_payload: dict[str, object] = {
        "category": hypothesis.category,
        "claim": hypothesis.claim,
        "supporting_evidence_ids": hypothesis.supporting_evidence_ids,
        "missing_evidence": hypothesis.missing_evidence,
    }
    if hypothesis.category == "prompt_constraint":
        return {
            **base_payload,
            "patch_policy": "only_add_missing_task_constraints",
            "forbidden_changes": ["model_id", "mode", "thinking", "media_uri", "scoring_standard"],
        }
    if hypothesis.category == "scoring_strictness":
        return {
            **base_payload,
            "scoring_variants": ["strict", "lenient_semantic"],
            "rerun_policy": "rescore_existing_outputs_first",
        }
    if hypothesis.category == "golden_answer_ambiguity":
        return {
            **base_payload,
            "comparison_policy": "semantic_equivalence_note_only",
            "may_replace_score": False,
        }
    if hypothesis.category == "model_stability":
        return {
            **base_payload,
            "rerun_policy": "same_prompt_same_media_locked_source",
        }
    if hypothesis.category == "input_evidence":
        return {
            **base_payload,
            "localization_policy": "narrow_evidence_window_without_model_change",
        }
    if hypothesis.category == "schema_constraint":
        return {
            **base_payload,
            "constraint_policy": "add_output_checklist_or_schema_only",
        }
    if hypothesis.category == "judge_disagreement":
        return {
            **base_payload,
            "crosscheck_policy": "judge_note_only",
            "may_replace_score": False,
        }
    return {
        **base_payload,
        "localization_policy": "verify_media_resolution_before_attribution",
    }


def _success_criteria(hypothesis: DebugHypothesis) -> dict[str, object]:
    if hypothesis.category == "prompt_constraint":
        return {
            "intervention_success_rate_gt_baseline": True,
            "must_preserve_locked_model_runner": True,
        }
    if hypothesis.category == "scoring_strictness":
        return {
            "lenient_score_gt_strict_score": True,
            "deterministic_rescore_only": True,
        }
    if hypothesis.category == "golden_answer_ambiguity":
        return {
            "semantic_equivalence_note": True,
            "does_not_override_deterministic_score": True,
        }
    if hypothesis.category == "model_stability":
        return {
            "variance_detected_across_locked_trials": True,
            "must_preserve_locked_model_runner": True,
        }
    if hypothesis.category == "judge_disagreement":
        return {
            "judge_note_conflict_identified": True,
            "does_not_override_deterministic_score": True,
        }
    return {
        "intervention_success_rate_gt_baseline": True,
        "must_preserve_locked_model_runner": True,
    }


def _stop_condition(requires_locked_model_runner: bool, *, trials: int) -> str:
    if requires_locked_model_runner:
        return f"stop after {trials} locked-source trial(s) or first deterministic pass"
    return "stop after deterministic non-runner comparison"

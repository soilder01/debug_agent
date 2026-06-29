from __future__ import annotations

from pydantic import BaseModel, Field

from debug_agent.debug_closure.hypotheses import DebugHypothesis, HypothesisClosurePayload


TERMINAL_PROBE_STATUSES = {"completed", "failed", "inconclusive"}


class DebugLoopPolicy(BaseModel):
    max_iterations: int = Field(default=3, ge=1, le=5)
    max_probe_plans_per_iteration: int = Field(default=6, ge=1, le=12)


DEFAULT_DEBUG_LOOP_POLICY = DebugLoopPolicy()


def current_iteration(payload: HypothesisClosurePayload) -> int:
    values = [
        *[item.iteration for item in payload.hypotheses],
        *[item.iteration for item in payload.probe_plans],
        *[item.iteration for item in payload.probe_results],
        *[item.iteration for item in payload.causal_comparisons],
    ]
    return max(values) if values else 1


def has_supported_comparison(payload: HypothesisClosurePayload) -> bool:
    return any(item.verdict == "supported" for item in payload.causal_comparisons)


def has_pending_probe(payload: HypothesisClosurePayload, *, iteration: int | None = None) -> bool:
    for result in payload.probe_results:
        if iteration is not None and result.iteration != iteration:
            continue
        if result.probe_job_id and result.status not in TERMINAL_PROBE_STATUSES:
            return True
    return False


def should_escalate_loop(
    *,
    payload: HypothesisClosurePayload,
    policy: DebugLoopPolicy = DEFAULT_DEBUG_LOOP_POLICY,
) -> bool:
    iteration = current_iteration(payload)
    if iteration >= policy.max_iterations:
        return False
    if has_supported_comparison(payload):
        return False
    if has_pending_probe(payload, iteration=iteration):
        return False
    return any(item.iteration == iteration for item in payload.causal_comparisons)


def next_iteration_hypotheses(
    *,
    current_iteration_value: int,
    evidence_ids: list[str],
) -> list[DebugHypothesis]:
    next_iteration = current_iteration_value + 1
    if next_iteration == 2:
        return _iteration_two_hypotheses(evidence_ids=evidence_ids)
    if next_iteration == 3:
        return _iteration_three_hypotheses(evidence_ids=evidence_ids)
    return []


def loop_budget_payload(policy: DebugLoopPolicy = DEFAULT_DEBUG_LOOP_POLICY) -> dict[str, object]:
    return {
        "max_iterations": policy.max_iterations,
        "max_probe_plans_per_iteration": policy.max_probe_plans_per_iteration,
        "stop_policy": (
            "stop when supported comparison exists, when runner probes are pending, "
            "or after max_iterations without supported evidence"
        ),
    }


def _iteration_two_hypotheses(*, evidence_ids: list[str]) -> list[DebugHypothesis]:
    return [
        DebugHypothesis(
            hypothesis_id="h2-input-evidence",
            category="input_evidence",
            claim=(
                "The failure may come from an incomplete or poorly localized input-evidence "
                "chain rather than the prompt patch itself."
            ),
            iteration=2,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["input_localization_probe"],
            confidence_before_probe="medium" if evidence_ids else "low",
        ),
        DebugHypothesis(
            hypothesis_id="h2-media-resolution",
            category="media_resolution",
            claim=(
                "The media attachment or resolved video may not be the evidence slice the "
                "task expects, so media resolution must be verified before attribution."
            ),
            iteration=2,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["media_resolution_probe"],
            confidence_before_probe="medium" if evidence_ids else "low",
        ),
        DebugHypothesis(
            hypothesis_id="h2-schema-constraint",
            category="schema_constraint",
            claim=(
                "The output schema or checklist may be too weak to force all required "
                "subtask details into the final JSON."
            ),
            iteration=2,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["schema_constraint_probe"],
            confidence_before_probe="medium" if evidence_ids else "low",
        ),
        DebugHypothesis(
            hypothesis_id="h2-judge-disagreement",
            category="judge_disagreement",
            claim=(
                "The deterministic judge may be rejecting semantically useful output for "
                "format or wording reasons that need cross-checking."
            ),
            iteration=2,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["judge_crosscheck_probe"],
            confidence_before_probe="low",
        ),
    ]


def _iteration_three_hypotheses(*, evidence_ids: list[str]) -> list[DebugHypothesis]:
    return [
        DebugHypothesis(
            hypothesis_id="h3-minimal-schema-patch",
            category="schema_constraint",
            claim=(
                "A minimal schema/checklist intervention should be tested as the final "
                "high-cost confirmation path before handoff."
            ),
            iteration=3,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["minimal_schema_patch_probe"],
            confidence_before_probe="medium" if evidence_ids else "low",
        ),
        DebugHypothesis(
            hypothesis_id="h3-localized-media-rerun",
            category="media_resolution",
            claim=(
                "A localized media rerun should confirm whether the required visual evidence "
                "is visible to the locked runner at all."
            ),
            iteration=3,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["localized_media_rerun_probe"],
            confidence_before_probe="medium" if evidence_ids else "low",
        ),
        DebugHypothesis(
            hypothesis_id="h3-high-trial-stability",
            category="model_stability",
            claim=(
                "A final locked high-trial stability probe should test whether the failure is "
                "a persistent model capability boundary instead of a one-off miss."
            ),
            iteration=3,
            supporting_evidence_ids=evidence_ids,
            missing_evidence=["high_trial_stability_probe"],
            confidence_before_probe="low",
        ),
    ]

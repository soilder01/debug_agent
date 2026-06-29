from __future__ import annotations

from debug_agent.debug_closure.hypotheses import CausalComparisonResult, DebugProbePlan


MIN_SIGNIFICANT_DELTA = 0.2


def compare_probe_outcome(
    *,
    plan: DebugProbePlan,
    baseline_success_rate: float,
    intervention_success_rate: float,
    evidence_ids: list[str],
    error_message: str = "",
) -> CausalComparisonResult:
    baseline = _bounded_rate(baseline_success_rate)
    intervention = _bounded_rate(intervention_success_rate)
    delta = round(intervention - baseline, 4)
    if error_message.strip():
        return _result(
            plan=plan,
            baseline=baseline,
            intervention=intervention,
            delta=delta,
            verdict="inconclusive",
            evidence_summary=f"Probe failed before causal comparison: {error_message.strip()}",
        )
    if plan.intervention_type in {"golden_equivalence", "judge_crosscheck"}:
        return _result(
            plan=plan,
            baseline=baseline,
            intervention=intervention,
            delta=delta,
            verdict="inconclusive",
            evidence_summary=(
                f"{plan.intervention_type} is note-only and cannot promote a root cause "
                f"without a controlled model-runner intervention. evidence={_joined(evidence_ids)}"
            ),
        )
    if plan.intervention_type == "stability_rerun":
        verdict = "supported" if 0.0 < intervention < 1.0 else "inconclusive"
        summary = (
            f"Locked reruns show variance: success_rate={intervention:.2f}."
            if verdict == "supported"
            else f"Locked reruns did not show enough variance: success_rate={intervention:.2f}."
        )
        return _result(
            plan=plan,
            baseline=baseline,
            intervention=intervention,
            delta=delta,
            verdict=verdict,
            evidence_summary=f"{summary} evidence={_joined(evidence_ids)}",
        )
    if delta >= MIN_SIGNIFICANT_DELTA:
        return _result(
            plan=plan,
            baseline=baseline,
            intervention=intervention,
            delta=delta,
            verdict="supported",
            evidence_summary=(
                f"Intervention improved success rate from {baseline:.2f} to {intervention:.2f} "
                f"(delta={delta:.2f}). evidence={_joined(evidence_ids)}"
            ),
        )
    if intervention <= baseline:
        return _result(
            plan=plan,
            baseline=baseline,
            intervention=intervention,
            delta=delta,
            verdict="rejected",
            evidence_summary=(
                f"Intervention did not improve success rate over baseline "
                f"({baseline:.2f} -> {intervention:.2f}). evidence={_joined(evidence_ids)}"
            ),
        )
    return _result(
        plan=plan,
        baseline=baseline,
        intervention=intervention,
        delta=delta,
        verdict="inconclusive",
        evidence_summary=(
            f"Intervention produced only a small lift ({baseline:.2f} -> {intervention:.2f}); "
            f"additional locked-source evidence is required. evidence={_joined(evidence_ids)}"
        ),
    )


def _result(
    *,
    plan: DebugProbePlan,
    baseline: float,
    intervention: float,
    delta: float,
    verdict: str,
    evidence_summary: str,
) -> CausalComparisonResult:
    return CausalComparisonResult(
        hypothesis_id=plan.hypothesis_id,
        probe_id=plan.probe_id,
        iteration=plan.iteration,
        baseline_success_rate=baseline,
        intervention_success_rate=intervention,
        delta=delta,
        verdict=verdict,  # type: ignore[arg-type]
        evidence_summary=evidence_summary,
    )


def _bounded_rate(value: float) -> float:
    return min(1.0, max(0.0, value))


def _joined(values: list[str]) -> str:
    return ", ".join(value for value in values if value.strip()) or "none"

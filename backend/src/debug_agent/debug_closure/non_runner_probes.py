from __future__ import annotations

import json
import re
from collections.abc import Iterable

from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure.hypotheses import DebugProbePlan, DebugProbeRunResult
from debug_agent.experiments.runner import ExperimentEvidence


SEMANTIC_EQUIVALENCE_THRESHOLD = 0.85
PARTIAL_SCORING_THRESHOLD = 0.7


def run_non_runner_probe(
    *,
    source_job_id: str,
    source_case: DebugCase,
    plan: DebugProbePlan,
    source_evidence: list[ExperimentEvidence],
) -> DebugProbeRunResult:
    evidence_ids = [item.evidence_id for item in source_evidence]
    if not source_evidence:
        return DebugProbeRunResult(
            probe_id=plan.probe_id,
            hypothesis_id=plan.hypothesis_id,
            iteration=plan.iteration,
            status="inconclusive",
            source_job_id=source_job_id,
            evidence_ids=[],
            error_message="source evidence is missing",
            diagnostic_summary="没有可复核的 source evidence，无法执行非 runner probe。",
        )
    observed_rate, summary = _observed_rate_for_plan(
        source_case=source_case,
        plan=plan,
        source_evidence=source_evidence,
    )
    return DebugProbeRunResult(
        probe_id=plan.probe_id,
        hypothesis_id=plan.hypothesis_id,
        iteration=plan.iteration,
        status="completed",
        source_job_id=source_job_id,
        evidence_ids=evidence_ids,
        observed_success_rate=observed_rate,
        diagnostic_summary=summary,
    )


def _observed_rate_for_plan(
    *,
    source_case: DebugCase,
    plan: DebugProbePlan,
    source_evidence: list[ExperimentEvidence],
) -> tuple[float, str]:
    if plan.intervention_type == "scoring_variant":
        return _scoring_variant_rate(source_case=source_case, source_evidence=source_evidence)
    if plan.intervention_type == "golden_equivalence":
        return _golden_equivalence_rate(source_case=source_case, source_evidence=source_evidence)
    if plan.intervention_type == "judge_crosscheck":
        return _judge_crosscheck_rate(source_case=source_case, source_evidence=source_evidence)
    return (
        0.0,
        f"{plan.intervention_type} is not a supported non-runner probe type.",
    )


def _scoring_variant_rate(
    *,
    source_case: DebugCase,
    source_evidence: list[ExperimentEvidence],
) -> tuple[float, str]:
    scores = [
        1.0
        if evidence.judge.score > 0
        else _lenient_semantic_score(
            expected_text=_expected_text(source_case=source_case, evidence=evidence),
            actual_text=_actual_text(evidence),
            threshold=PARTIAL_SCORING_THRESHOLD,
        )
        for evidence in source_evidence
    ]
    rate = _average(scores)
    return (
        rate,
        (
            "scoring_variant 使用现有 source output 做宽松语义重判；"
            f"lenient_success_rate={rate:.2f}，strict_success_rate="
            f"{_strict_rate(source_evidence):.2f}。"
        ),
    )


def _golden_equivalence_rate(
    *,
    source_case: DebugCase,
    source_evidence: list[ExperimentEvidence],
) -> tuple[float, str]:
    scores = [
        _lenient_semantic_score(
            expected_text=_expected_text(source_case=source_case, evidence=evidence),
            actual_text=_actual_text(evidence),
            threshold=SEMANTIC_EQUIVALENCE_THRESHOLD,
        )
        for evidence in source_evidence
    ]
    rate = _average(scores)
    return (
        rate,
        (
            "golden_equivalence 仅判断输出与标答是否语义等价；"
            f"equivalence_rate={rate:.2f}。该结果不能单独提升为 verified root cause。"
        ),
    )


def _judge_crosscheck_rate(
    *,
    source_case: DebugCase,
    source_evidence: list[ExperimentEvidence],
) -> tuple[float, str]:
    scores = [
        _lenient_semantic_score(
            expected_text=_expected_text(source_case=source_case, evidence=evidence),
            actual_text=_actual_text(evidence),
            threshold=SEMANTIC_EQUIVALENCE_THRESHOLD,
        )
        for evidence in source_evidence
        if evidence.judge.deltas or evidence.judge.reasons
    ]
    rate = _average(scores)
    return (
        rate,
        (
            "judge_crosscheck 使用现有 judge delta 做语义冲突复核；"
            f"conflict_equivalence_rate={rate:.2f}。该结果只作为解释性证据。"
        ),
    )


def _expected_text(*, source_case: DebugCase, evidence: ExperimentEvidence) -> str:
    delta_expected = [
        str(delta.get("expected", ""))
        for delta in evidence.judge.deltas
        if isinstance(delta, dict) and delta.get("expected") is not None
    ]
    if delta_expected:
        return " ".join(delta_expected)
    return _json_text(source_case.expected_output)


def _actual_text(evidence: ExperimentEvidence) -> str:
    delta_actual = [
        str(delta.get("actual", ""))
        for delta in evidence.judge.deltas
        if isinstance(delta, dict) and delta.get("actual") is not None
    ]
    return " ".join([evidence.raw_output, *delta_actual])


def _lenient_semantic_score(*, expected_text: str, actual_text: str, threshold: float) -> float:
    expected_terms = _semantic_terms(expected_text)
    actual_terms = _semantic_terms(actual_text)
    if not expected_terms or not actual_terms:
        return 0.0
    overlap = len(expected_terms & actual_terms) / len(expected_terms)
    return 1.0 if overlap >= threshold else 0.0


def _semantic_terms(value: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", value.lower())
    return {token for token in tokens if token.strip()}


def _average(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def _strict_rate(source_evidence: list[ExperimentEvidence]) -> float:
    return _average(1.0 if item.judge.score > 0 else 0.0 for item in source_evidence)


def _json_text(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)

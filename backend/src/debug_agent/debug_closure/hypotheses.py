from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


HypothesisCategory = Literal[
    "prompt_constraint",
    "scoring_strictness",
    "golden_answer_ambiguity",
    "model_stability",
    "input_evidence",
    "schema_constraint",
    "judge_disagreement",
    "media_resolution",
]

HypothesisStatus = Literal["candidate", "supported", "rejected", "inconclusive"]
ProbeInterventionType = Literal[
    "prompt_patch",
    "scoring_variant",
    "golden_equivalence",
    "stability_rerun",
    "input_localization",
    "schema_constraint",
    "judge_crosscheck",
]
CausalVerdict = Literal["supported", "rejected", "inconclusive"]


class DebugHypothesis(BaseModel):
    hypothesis_id: str
    category: HypothesisCategory
    claim: str
    iteration: int = Field(default=1, ge=1, le=10)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence_before_probe: Literal["low", "medium", "high"] = "low"
    status: HypothesisStatus = "candidate"

    @field_validator("hypothesis_id", "claim")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("supporting_evidence_ids", "missing_evidence")
    @classmethod
    def _deduplicate_text_items(cls, values: list[str]) -> list[str]:
        deduplicated: list[str] = []
        seen: set[str] = set()
        for value in values:
            stripped = value.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            deduplicated.append(stripped)
        return deduplicated


class DebugProbePlan(BaseModel):
    probe_id: str
    hypothesis_id: str
    intervention_type: ProbeInterventionType
    iteration: int = Field(default=1, ge=1, le=10)
    intervention_payload: dict[str, object] = Field(default_factory=dict)
    model_runner_config_ref: Literal["locked_source"] = "locked_source"
    trials: int = Field(default=1, ge=1, le=20)
    success_criteria: dict[str, object] = Field(default_factory=dict)
    stop_condition: str

    @field_validator("probe_id", "hypothesis_id", "stop_condition")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class DebugProbeRunResult(BaseModel):
    probe_id: str
    hypothesis_id: str
    iteration: int = Field(default=1, ge=1, le=10)
    status: Literal["not_run", "running", "completed", "failed", "inconclusive"] = "not_run"
    source_job_id: str = ""
    probe_job_id: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    error_message: str = ""
    observed_success_rate: float | None = Field(default=None, ge=0, le=1)
    diagnostic_summary: str = ""
    model_runner_config_snapshot: dict[str, object] = Field(default_factory=dict)


class CausalComparisonResult(BaseModel):
    hypothesis_id: str
    probe_id: str
    iteration: int = Field(default=1, ge=1, le=10)
    baseline_success_rate: float = Field(ge=0, le=1)
    intervention_success_rate: float = Field(ge=0, le=1)
    delta: float
    verdict: CausalVerdict
    evidence_summary: str

    @field_validator("hypothesis_id", "probe_id", "evidence_summary")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class HypothesisClosurePayload(BaseModel):
    hypotheses: list[DebugHypothesis] = Field(default_factory=list)
    probe_plans: list[DebugProbePlan] = Field(default_factory=list)
    probe_results: list[DebugProbeRunResult] = Field(default_factory=list)
    causal_comparisons: list[CausalComparisonResult] = Field(default_factory=list)
    fairness_lock: dict[str, object] = Field(default_factory=dict)


def normalize_hypotheses(hypotheses: list[DebugHypothesis]) -> list[DebugHypothesis]:
    normalized: list[DebugHypothesis] = []
    seen: set[str] = set()
    for hypothesis in hypotheses:
        if hypothesis.hypothesis_id in seen:
            continue
        seen.add(hypothesis.hypothesis_id)
        normalized.append(_normalize_hypothesis(hypothesis))
    return normalized


def _normalize_hypothesis(hypothesis: DebugHypothesis) -> DebugHypothesis:
    updates: dict[str, object] = {"status": "candidate"}
    if not hypothesis.supporting_evidence_ids:
        updates["confidence_before_probe"] = "low"
    return hypothesis.model_copy(update=updates)

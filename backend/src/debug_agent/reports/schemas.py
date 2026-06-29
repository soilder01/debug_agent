from __future__ import annotations

from pydantic import BaseModel, Field


class ObservedFailure(BaseModel):
    type: str
    summary: str
    affected_box_ids: list[int]


class RootCause(BaseModel):
    label: str
    confidence: str
    evidence_summary: str


class ExperimentSummary(BaseModel):
    total_trials: int
    success_count: int
    failed_trial_count: int = 0
    success_rate: float = 0.0
    stability_label: str = "not_run"
    evidence_ids: list[str]
    artifact_ids: list[str] = Field(default_factory=list)
    artifact_evidence_links: list[dict[str, str]] = Field(default_factory=list)
    image_artifact_ids: list[str]
    step_summaries: list[dict[str, object]] = Field(default_factory=list)


class AgentTrace(BaseModel):
    agent_role: str
    input_summary: dict[str, object] = Field(default_factory=dict)
    input_excerpt: str = ""
    input_sha256: str = ""
    output_summary: dict[str, object] = Field(default_factory=dict)
    output_excerpt: str = ""
    reasoning_summary: str = ""
    raw_cot_policy: str = "visible_output_summary_only"


class DebugReport(BaseModel):
    job_id: str | None = None
    case_id: str
    status: str
    report_document_url: str = ""
    product_summary: dict[str, str] = Field(default_factory=dict)
    observed_failure: ObservedFailure
    planned_experiments: list[str]
    experiment_summary: ExperimentSummary | None = None
    root_cause: RootCause
    evidence_citations: list[dict[str, object]] = Field(default_factory=list)
    root_cause_trace: list[dict[str, object]] = Field(default_factory=list)
    recommended_actions: list[dict[str, str]] = Field(default_factory=list)
    action_queue: list[dict[str, object]] = Field(default_factory=list)
    run_view: dict[str, object] = Field(default_factory=dict)
    verification_results: list[dict[str, object]] = Field(default_factory=list)
    evaluation_asset_diagnostics: list[dict[str, str]] = Field(default_factory=list)
    follow_up_experiments: list[dict[str, str]] = Field(default_factory=list)
    strategy_follow_up_results: list[dict[str, object]] = Field(default_factory=list)
    targeted_probe_results: list[dict[str, object]] = Field(default_factory=list)
    human_handoff_requests: list[dict[str, str]] = Field(default_factory=list)
    human_handoff_statuses: list[dict[str, str]] = Field(default_factory=list)
    final_attributions: list[dict[str, str]] = Field(default_factory=list)
    final_attribution_verification_results: list[dict[str, object]] = Field(default_factory=list)
    final_attribution_recovery_results: list[dict[str, object]] = Field(default_factory=list)
    supplemental_contexts: list[dict[str, object]] = Field(default_factory=list)
    confidence_reasons: list[dict[str, str]] = Field(default_factory=list)
    debug_strategy: list[dict[str, str]] = Field(default_factory=list)
    judge_comparison_notes: list[dict[str, str]] = Field(default_factory=list)
    meta_agent_enrichment: dict[str, object] = Field(default_factory=dict)
    agent_traces: list[AgentTrace] = Field(default_factory=list)
    suggested_sheet_fields: dict[str, str]

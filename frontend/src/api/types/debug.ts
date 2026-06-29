export type ActionQueueItem = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  priority: string;
  state: string;
  state_label: string;
  source: string;
  source_ref: string;
  owner: string;
  status: string;
  status_updated_at: string;
  verification_job_id: string;
  verification_result: string;
  verification_summary: string;
  writeback_status: string;
  writeback_row_id: string;
  writeback_report_url: string;
  evidence_ids: string;
  artifact_ids: string;
  trace_refs: string;
  available_operations: string[];
  next_operation: string;
};

export type ActionQueueResponse = {
  job_id: string;
  summary: Record<string, number>;
  items: ActionQueueItem[];
};

export type DebugRunHypothesisClosure = {
  status: string;
  status_label: string;
  summary: string;
  hypothesis_count: number;
  probe_plan_count: number;
  probe_result_count: number;
  causal_comparison_count: number;
  verified_root_cause_count: number;
  unverified_hypothesis_count: number;
  fairness_lock: Record<string, unknown>;
  hypotheses: Array<Record<string, unknown>>;
  probe_plans: Array<Record<string, unknown>>;
  probe_results: Array<Record<string, unknown>>;
  causal_comparisons: Array<Record<string, unknown>>;
  verified_root_causes: Array<Record<string, unknown>>;
  unverified_hypotheses: Array<Record<string, unknown>>;
};

export type DebugRunLoop = {
  status: string;
  status_label: string;
  summary: string;
  current_iteration: number;
  decision: string;
  next_action: string;
  stop_reason: string;
  iterations: Array<Record<string, unknown>>;
};

export type DebugRunView = {
  job: {
    job_id: string;
    case_id: string;
    status: string;
    status_label: string;
    created_at: string;
    updated_at: string;
  };
  summary: {
    headline: string;
    current_phase: string;
    next_step: string;
    evidence_count: number;
    agent_trace_count: number;
  };
  timeline: Array<{
    key: string;
    label: string;
    status: string;
    status_label: string;
    summary: string;
    started_at: string;
    updated_at: string;
  }>;
  agent_traces: Array<{
    agent_role: string;
    reasoning_summary?: string;
    [key: string]: unknown;
  }>;
  auto_closure: {
    status: string;
    status_label: string;
    summary: string;
    stage_count: number;
  };
  debug_loop?: DebugRunLoop;
  hypothesis_closure?: DebugRunHypothesisClosure;
  writeback: {
    status: string;
    status_label: string;
    row_id: string;
    report_url: string;
    error_message: string;
    updated_at: string;
  };
  action_queue: {
    summary: Record<string, number>;
    items: ActionQueueItem[];
  };
};

export type DebugReport = {
  job_id: string | null;
  case_id: string;
  status: string;
  product_summary?: {
    root_cause_label: string;
    failure_summary: string;
    evidence_source: string;
    confidence_explanation: string;
    next_action: string;
  };
  observed_failure: {
    type: string;
    summary: string;
    affected_box_ids: number[];
  };
  planned_experiments: string[];
  experiment_summary: {
    total_trials: number;
    success_count: number;
    failed_trial_count?: number;
    success_rate?: number;
    stability_label?: string;
    evidence_ids: string[];
    artifact_ids?: string[];
    artifact_evidence_links?: Array<{
      artifact_id: string;
      evidence_id: string;
    }>;
    image_artifact_ids?: string[];
    step_summaries?: Array<{
      step_name: string;
      total_trials: number;
      success_count: number;
      failed_trial_count: number;
      success_rate: number;
      delta_reasons: string[];
      target_ids: string[];
      evidence_ids: string[];
      artifact_ids: string[];
      ablation_variants?: string[];
      ablation_modalities?: string[];
    }>;
  } | null;
  root_cause: {
    label: string;
    confidence: string;
    evidence_summary: string;
  };
  evidence_citations?: Array<{
    evidence_id: string;
    step_name: string;
    box_id: number | null;
    reason: string;
    artifact_ids: string[];
  }>;
  root_cause_trace?: Array<{
    step_name: string;
    variant: string;
    modalities: string[];
    evidence_id: string;
    judge_score: number;
    delta_reasons: string[];
    target_ids: string[];
    artifact_ids: string[];
    hypothesis?: string;
    observation?: string;
    conclusion?: string;
    next_probe?: string;
  }>;
  recommended_actions?: Array<{
    category: string;
    priority: string;
    status?: string;
    summary: string;
    detail: string;
    evidence_ids?: string;
    artifact_ids?: string;
    trace_refs?: string;
  }>;
  action_queue?: ActionQueueItem[];
  run_view?: DebugRunView;
  verification_results?: RecommendedActionVerificationResult[];
  targeted_probe_results?: Array<{
    source_job_id: string;
    target_id: string;
    planned_steps: string;
    probe_job_id: string;
    actor: string;
    note: string;
    created_at: string;
    outcome: string;
    success_rate: number;
    summary: string;
    escalation: string;
  }>;
  human_handoff_requests?: Array<{
    source: string;
    target_id: string;
    priority: string;
    reason: string;
    summary: string;
    recommended_owner: string;
    next_action: string;
  }>;
  human_handoff_statuses?: HumanHandoffStatus[];
  final_attributions?: Array<{
    source: string;
    target_id: string;
    category: string;
    status: string;
    actor: string;
    summary: string;
    recommended_action: string;
  }>;
  final_attribution_verification_results?: Array<{
    source: string;
    target_id: string;
    category: string;
    verification_job_id: string;
    result: string;
    success_rate: number;
    summary: string;
  }>;
  final_attribution_recovery_results?: Array<{
    source: string;
    target_id: string;
    category: string;
    recovery_job_id: string;
    result: string;
    success_rate: number;
    summary: string;
  }>;
  evaluation_asset_diagnostics?: Array<{
    source: string;
    status: string;
    severity: string;
    summary: string;
    recommendation: string;
    evidence_ids?: string;
    artifact_ids?: string;
    trace_refs?: string;
  }>;
  confidence_reasons?: Array<{
    source: string;
    level: string;
    summary: string;
    evidence_ids?: string;
    artifact_ids?: string;
    trace_refs?: string;
  }>;
  debug_strategy?: Array<{
    stage: string;
    objective: string;
    trigger: string;
    planned_probe: string;
    stop_condition: string;
    escalation: string;
  }>;
  judge_comparison_notes?: Array<{
    evidence_id: string;
    target_id: string;
    deterministic_reason: string;
    llm_note: string;
    risk: string;
  }>;
  follow_up_experiments?: Array<{
    source: string;
    stage?: string;
    target_id?: string;
    category?: string;
    parent_probe_job_id?: string;
    verification_job_id?: string;
    result?: string;
    stop_condition?: string;
    planned_steps: string;
    summary: string;
  }>;
  meta_agent_enrichment?: Record<string, unknown>;
  suggested_sheet_fields: Record<string, string>;
};

export type AssistantCitation = {
  title: string;
  source: string;
  snippet: string;
};

export type AssistantChatResponse = {
  answer: string;
  citations: AssistantCitation[];
  model_provider: string;
  model_id: string;
};


export type RecommendedActionStatusValue = "pending" | "accepted" | "rejected" | "applied";

export type RecommendedActionStatus = {
  job_id: string;
  action_index: number;
  status: RecommendedActionStatusValue;
  actor: string;
  note: string;
  created_at: string;
  updated_at: string;
};

export type RecommendedActionStatusEvent = {
  event_id: number;
  job_id: string;
  action_index: number;
  status: RecommendedActionStatusValue;
  actor: string;
  note: string;
  created_at: string;
};

export type RecommendedActionVerification = {
  job_id: string;
  action_index: number;
  verification_job_id: string;
  actor: string;
  note: string;
  created_at: string;
};

export type RecommendedActionVerificationResponse = RecommendedActionVerification & {
  verification_job: SubmittedDebugJob;
};

export type StrategyFollowUpJob = {
  source_job_id: string;
  stage: string;
  planned_steps: string;
  follow_up_job_id: string;
  actor: string;
  note: string;
  created_at: string;
  outcome: "pending" | "passed_stop_condition" | "needs_escalation" | "inconclusive";
  success_rate: number;
  summary: string;
  escalation: string;
};

export type StrategyFollowUpJobResponse = StrategyFollowUpJob & {
  follow_up_job: SubmittedDebugJob;
};

export type TargetedProbeJob = {
  source_job_id: string;
  source: string;
  target_id: string;
  planned_steps: string;
  probe_job_id: string;
  parent_probe_job_id: string;
  trigger_outcome: string;
  actor: string;
  note: string;
  created_at: string;
  outcome?: "pending" | "target_cleared" | "target_still_failing" | "inconclusive";
  success_rate?: number;
  summary?: string;
  escalation?: string;
};

export type TargetedProbeJobResponse = TargetedProbeJob & {
  probe_job: SubmittedDebugJob;
};

export type AutoDebugClosureResult = {
  source_job_id: string;
  created_targeted_probe_jobs: string[];
  created_strategy_follow_up_jobs: string[];
  created_verification_jobs: string[];
  hypotheses?: Array<Record<string, unknown>>;
  probe_plans?: Array<Record<string, unknown>>;
  probe_results?: Array<Record<string, unknown>>;
  causal_comparisons?: Array<Record<string, unknown>>;
  verified_root_causes?: Array<Record<string, unknown>>;
  unverified_hypotheses?: Array<Record<string, unknown>>;
  fairness_lock?: Record<string, unknown>;
  evidence_summaries: Array<{
    job_id: string;
    evidence_id: string;
    step_name: string;
    trial: string;
    judge_score: string;
    delta_reasons: string[];
    raw_output_excerpt: string;
    model_call_error: string;
    response_parse_error: string;
  }>;
  targeted_probe_outcomes: Array<{
    probe_job_id: string;
    target_id: string;
    outcome: string;
    summary: string;
  }>;
  final_attribution_candidates: Array<{
    category: string;
    confidence: string;
    summary: string;
  }>;
  badcase_live_comparison: {
    original_badcase: string;
    live_rerun: string;
    decision: string;
  };
  writeback_status: string;
};

export type AutoDebugClosureReportResponse = {
  source_job_id: string;
  closure: AutoDebugClosureResult;
  markdown: string;
  report_artifact_url: string;
};

export type DebugRunStage = {
  job_id: string;
  stage: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  failure_reason: string;
  retryable: boolean;
  attempt_count: number;
  created_at: string;
  updated_at: string;
};

export type DebugRunStageListResponse = {
  stages: DebugRunStage[];
};

export type EvidenceLedgerRecord = {
  job_id: string;
  evidence_id: string;
  step_name: string;
  prompt: Record<string, unknown>;
  enhanced_constraints: Record<string, unknown>;
  raw_output: string;
  parsed_result: Record<string, unknown>;
  judge_version: string;
  score_delta: Record<string, unknown>;
  artifact_links: Array<Record<string, unknown>>;
};

export type EvidenceLedgerResponse = {
  records: EvidenceLedgerRecord[];
};

export type HumanHandoffStatusValue = "pending" | "acknowledged" | "in_progress" | "resolved" | "wont_fix";

export type HumanHandoffStatus = {
  job_id: string;
  target_id: string;
  status: HumanHandoffStatusValue;
  actor: string;
  note: string;
  created_at: string;
  updated_at: string;
};

export type StrategyFollowUpJobListResponse = {
  follow_ups: StrategyFollowUpJob[];
};

export type TargetedProbeJobListResponse = {
  probes: TargetedProbeJob[];
};

export type HumanHandoffStatusListResponse = {
  statuses: HumanHandoffStatus[];
};

export type RecommendedActionVerificationResult = {
  job_id: string;
  action_index: number;
  verification_job_id: string;
  result: "pending" | "resolved" | "not_resolved" | "regressed" | "inconclusive";
  source_success_rate: number;
  verification_success_rate: number;
  source_root_cause: string;
  verification_root_cause: string;
  summary: string;
};

export type RecommendedActionStatusListResponse = {
  statuses: RecommendedActionStatus[];
  events: RecommendedActionStatusEvent[];
  verifications: RecommendedActionVerification[];
  verification_results: RecommendedActionVerificationResult[];
};

export type RetryRecommendationDetail = {
  code: string;
  label: string;
  action: string;
  severity: string;
};

export type SubmittedDebugJob = {
  job_id: string;
  case_id: string;
  artifact_group_id?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  attempt_count?: number;
  max_attempts?: number;
  remaining_attempts?: number;
  will_retry?: boolean;
  retry_recommendation?: string;
  retry_recommendation_detail?: RetryRecommendationDetail;
  error_message?: string | null;
  evidence_ids?: string[];
};

export type DebugJobStatus = {
  job_id: string;
  case_id: string;
  artifact_group_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
  attempt_count: number;
  max_attempts: number;
  remaining_attempts: number;
  will_retry: boolean;
  retry_recommendation: string;
  retry_recommendation_detail: RetryRecommendationDetail;
  error_message: string | null;
  evidence_ids: string[];
  evidence_error_counts: {
    total_evidence: number;
    failed_judgements: number;
    response_parse_errors: number;
    model_call_errors: number;
  };
  spreadsheet_writeback_audit: SpreadsheetWritebackAuditSummary | null;
};

export type SpreadsheetWritebackAuditSummary = {
  status: string;
  row_id: string;
  report_url: string;
  error_message: string;
  updated_at: string;
};

export type BatchDebugJobResponse = {
  batch_id?: string;
  batch?: DebugBatchProgress;
  jobs: SubmittedDebugJob[];
  rejected_case_ids: string[];
};

export type AgentModelSelection = {
  provider: string;
  model_id: string;
  base_url?: string;
  credential_ref?: string;
  mode?: string;
  thinking?: "enabled" | "disabled";
  temperature?: number | null;
  top_p?: number | null;
  max_tokens?: number | null;
  locked?: boolean;
};

export type AgentModelConfig = {
  roles: Record<string, AgentModelSelection>;
};

export type ModelCatalogOption = {
  provider: string;
  model_id: string;
  label: string;
  description: string;
  modes: string[];
  supports_thinking: boolean;
  supports_vision: boolean;
  supports_video: boolean;
  locked_for_roles: string[];
  default_parameters: Record<string, unknown>;
  source: string;
};

export type AgentModelRuntimeConfig = {
  default_config: AgentModelConfig;
  catalog: ModelCatalogOption[];
};

export type AgentRoleDefinition = {
  role_id: string;
  display_name: string;
  worker_name: string;
  responsibility: string;
  default_model_tier: string;
  locked: boolean;
  owned_stages: string[];
};

export type DebugStageDefinition = {
  stage_id: string;
  display_name: string;
  owner_roles: string[];
  source_replay: boolean;
};

export type ModelCatalogResponse = {
  runtime: AgentModelRuntimeConfig;
  agent_roles: AgentRoleDefinition[];
  debug_stages: DebugStageDefinition[];
  live_models: ModelCatalogOption[];
  live_model_count: number;
  live_probe_error: string;
};

export type AgentModelConnectionTestRequest = {
  provider: "ark" | "api";
  base_url: string;
  api_key?: string;
  model_id?: string;
};

export type AgentModelConnectionTestResponse = {
  ok: boolean;
  message: string;
  model_count: number;
  model_found: boolean;
  credential_ref: string;
};

export type BatchDebugJobRequest = {
  caseIds: string[];
  maxConcurrency?: number;
  agentModelConfig?: AgentModelConfig;
};

export type DebugBatch = {
  batch_id: string;
  status: string;
  total_jobs: number;
  max_concurrency: number;
  retry_policy: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at: string;
  completed_at: string;
};

export type DebugJobAttempt = {
  job_id: string;
  attempt_index: number;
  batch_id: string;
  status: string;
  failure_type: string;
  failure_stage: string;
  error_message: string;
  retry_decision: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
};

export type DebugBatchProgress = {
  batch: DebugBatch;
  status_counts: Record<string, number>;
  failure_types: Record<string, number>;
  failure_stages: Record<string, number>;
  metrics: Record<string, number>;
  agent_metrics: Record<string, Record<string, number>>;
  evaluation_summary?: DebugBatchEvaluationSummary;
  progress_percent: number;
  pending_count: number;
  running_count: number;
  completed_count: number;
  failed_count: number;
  recent_jobs: DebugJobStatus[];
  recent_attempts: DebugJobAttempt[];
};

export type DebugBatchEvaluationSummary = {
  row_count: number;
  created_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  running_jobs: number;
  success_rate: number;
  failure_rate: number;
  average_duration_ms: number;
  p50_duration_ms: number;
  p95_duration_ms: number;
  max_duration_ms: number;
  retry_scheduled_count: number;
  model_call_count: number;
  model_call_errors: number;
  estimated_cost_units: number;
  writeback_succeeded: number;
  writeback_failed: number;
  writeback_skipped: number;
  speed_label: string;
  cost_label: string;
  stability_label: string;
  trust_label: string;
  comparison_summary: string;
};

export type DebugBatchComparisonItem = {
  batch_id: string;
  status: string;
  total_jobs: number;
  model_profile: string;
  model_runner_model: string;
  model_runner_locked: boolean;
  thinking_enabled_roles: string[];
  success_rate: number;
  p95_duration_ms: number;
  estimated_cost_units: number;
  model_call_errors: number;
  writeback_failed: number;
  quality_score: number;
  efficiency_score: number;
  summary: string;
};

export type DebugBatchComparisonResponse = {
  generated_at: string;
  batch_ids: string[];
  items: DebugBatchComparisonItem[];
  best_batch_id: string;
  summary: string;
  export_url: string;
};

export type DebugBatchListResponse = {
  batches: DebugBatchProgress[];
};

export type DebugJobListResponse = {
  jobs: DebugJobStatus[];
  total_count: number;
};

export type DebugCaseSummary = {
  case_id: string;
  image_uri: string;
  avg_score: number;
  debug_status: string;
  root_cause: string;
  box_region_count?: number;
};

export type DebugCaseListResponse = {
  cases: DebugCaseSummary[];
  total_count: number;
  filtered_count?: number;
};

export type ImageArtifact = {
  artifact_id: string;
  kind: string;
  source_image_uri: string;
  derived_image_uri: string;
  preview_image_url?: string;
  region: {
    x: number;
    y: number;
    width: number;
    height: number;
    unit: string;
    label: string;
  } | null;
};

export type EvidenceArtifact = {
  artifact_id: string;
  kind: string;
  artifact_type: string;
  source_uri: string;
  derived_uri: string;
  preview_url?: string;
  region: {
    x: number;
    y: number;
    width: number;
    height: number;
    unit: string;
    label: string;
  } | null;
  metadata: Record<string, unknown>;
};

export type JudgeDelta = {
  target_id: string;
  expected: string | null;
  actual: string | null;
  reason: string;
  metadata: Record<string, unknown>;
};

export type DebugCaseDetail = {
  case_id: string;
  image_uri: string;
  prompt: string;
  golden_answer: {
    answers: Array<{
      box_id: number;
      student_answer: string;
    }>;
  };
  expected_output?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  scoring_standard: string;
  predictions: Array<{
    trial: number;
    raw_output: string;
    score: number;
  }>;
  avg_score: number;
  human_notes: {
    debug_status: string;
    root_cause: string;
  };
  box_regions?: Array<{
    box_id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    unit: string;
    label: string;
  }>;
};

export type WorkerStatus = {
  running: boolean;
  max_concurrency?: number;
  active_count?: number;
  processed_count: number;
  error_count: number;
  recovered_stale_job_count?: number;
  last_error: string | null;
  completion_hook_enabled: boolean;
  report_base_url: string;
  auto_writeback_enabled: boolean;
};

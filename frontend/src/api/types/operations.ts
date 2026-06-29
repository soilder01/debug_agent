import type { DebugBatchComparisonResponse, WorkerStatus } from "./debug";
import type { SpreadsheetWritebackAuditCounts } from "./spreadsheets";

export type ObservabilitySummary = {
  jobs: {
    by_status: Record<string, number>;
    total_count: number;
    pending_count: number;
    running_count: number;
    failed_count: number;
    completed_count: number;
  };
  worker: WorkerStatus;
  writeback_audits: SpreadsheetWritebackAuditCounts;
  evidence: {
    total_evidence: number;
    failed_judgements: number;
    response_parse_errors: number;
    model_call_errors: number;
    average_latency_ms: number;
  };
  strategy_feedback: {
    total_follow_ups: number;
    pending_count: number;
    passed_stop_condition_count: number;
    needs_escalation_count: number;
  };
  targeted_probe_feedback?: {
    total_probes: number;
    pending_count: number;
    target_cleared_count: number;
    target_still_failing_count: number;
    inconclusive_count: number;
    max_depth_reached_count: number;
  };
  human_handoff_feedback?: {
    total_handoffs: number;
    pending_count: number;
    acknowledged_count: number;
    in_progress_count: number;
    resolved_count: number;
    wont_fix_count: number;
    open_count: number;
  };
  final_attribution_verification_feedback?: {
    total_verifications: number;
    pending_count: number;
    resolved_count: number;
    not_resolved_count: number;
    inconclusive_count: number;
  };
  final_attribution_recovery_feedback?: {
    total_recoveries: number;
    pending_count: number;
    closed_count: number;
    reopen_count: number;
    inconclusive_count: number;
  };
  usage: {
    model_call_count: number;
    prompt_character_count: number;
    estimated_cost_units: number;
    budget_units: number;
    budget_status: "not_configured" | "within_budget" | "over_budget";
    budget_utilization: number;
    budget_enforcement_enabled: boolean;
  };
  health: {
    level: "healthy" | "degraded" | "critical";
    reasons: string[];
    actions: string[];
  };
  performance?: PerformanceSummary;
};

export type PerformanceAggregate = {
  component: string;
  operation: string;
  count: number;
  failed_count: number;
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  max_ms: number;
  latest_ms: number;
};

export type PerformanceEvent = {
  component: string;
  operation: string;
  duration_ms: number;
  status: string;
  metadata: Record<string, unknown>;
  occurred_at: string;
};

export type PerformanceSummary = {
  total_count: number;
  aggregates: PerformanceAggregate[];
  recent_events: PerformanceEvent[];
};

export type RuntimePathStatus = {
  name: string;
  label: string;
  path: string;
  exists: boolean;
  is_directory: boolean;
  writable: boolean;
};

export type RuntimeConfigSummary = {
  environment: string;
  database_url: string;
  database_kind: string;
  database_path: string;
  artifact_root: string;
  artifact_retention_days: number;
  report_base_url: string;
  auto_writeback_enabled: boolean;
  queue_max_concurrency: number;
  retry_max_attempts: number;
  stale_running_job_seconds: number;
  require_trusted_actor: boolean;
  enable_fixture_fallback: boolean;
  usage_budget_units: number;
  enforce_usage_budget: boolean;
  lark_configured: boolean;
  lark_connector_mode: string;
  lark_identity: string;
  lark_profile: string;
  lark_event_mode: "webhook" | "long_connection";
  lark_bot_verification_configured: boolean;
  lark_bot_encrypt_configured: boolean;
  worker_running: boolean;
  worker_completion_hook_enabled: boolean;
};

export type ProductionReadinessCheck = {
  key: string;
  label: string;
  status: "ok" | "warning" | "critical";
  detail: string;
  action: string;
};

export type ProductionReadiness = {
  generated_at: string;
  level: "healthy" | "degraded" | "critical";
  config: RuntimeConfigSummary;
  paths: RuntimePathStatus[];
  checks: ProductionReadinessCheck[];
  export_urls: Record<string, string>;
};

export type PilotGateThresholds = {
  min_completed_jobs: number;
  min_success_rate: number;
  max_p95_duration_ms: number;
  max_estimated_cost_units: number;
  max_model_call_errors: number;
  max_writeback_failed: number;
  max_lark_operation_failures: number;
};

export type PilotGateBatchEvidence = {
  compared_batch_count: number;
  completed_jobs: number;
  best_batch_id: string;
  best_success_rate: number;
  best_p95_duration_ms: number;
  best_estimated_cost_units: number;
  best_quality_score: number;
  best_efficiency_score: number;
};

export type PilotGateCheck = {
  key: string;
  label: string;
  status: "passed" | "warning" | "failed";
  detail: string;
  action: string;
};

export type PilotGate = {
  generated_at: string;
  status: "passed" | "warning" | "failed";
  thresholds: PilotGateThresholds;
  batch_evidence: PilotGateBatchEvidence;
  checks: PilotGateCheck[];
  comparison: DebugBatchComparisonResponse;
  export_urls: Record<string, string>;
};

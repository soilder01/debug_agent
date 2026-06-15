export type DebugReport = {
  job_id: string | null;
  case_id: string;
  status: string;
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
  }>;
  verification_results?: RecommendedActionVerificationResult[];
  evaluation_asset_diagnostics?: Array<{
    source: string;
    status: string;
    severity: string;
    summary: string;
    recommendation: string;
  }>;
  confidence_reasons?: Array<{
    source: string;
    level: string;
    summary: string;
  }>;
  suggested_sheet_fields: Record<string, string>;
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
  jobs: SubmittedDebugJob[];
  rejected_case_ids: string[];
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
  processed_count: number;
  error_count: number;
  last_error: string | null;
  completion_hook_enabled: boolean;
  report_base_url: string;
  auto_writeback_enabled: boolean;
};

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
};

export type JsonlRejectedLine = {
  line_number: number;
  error_message: string;
};

export type JsonlImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_lines: JsonlRejectedLine[];
};

export type CsvRejectedRow = {
  row_number: number;
  error_message: string;
};

export type CsvImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_rows: CsvRejectedRow[];
};

export type SpreadsheetImportedRowResponse = {
  sheet_row_id: string;
  case_id: string;
};

export type SpreadsheetRejectedRow = {
  row_index: number;
  sheet_row_id: string;
  error_message: string;
};

export type SpreadsheetRowImportResponse = {
  imported_case_ids: string[];
  imported_rows: SpreadsheetImportedRowResponse[];
  jobs: SubmittedDebugJob[];
  rejected_rows: SpreadsheetRejectedRow[];
};

export type SpreadsheetSyncResponse = SpreadsheetRowImportResponse;

export type SpreadsheetWritebackResult = {
  row_id: string;
  fields: Record<string, string>;
};

export type SpreadsheetWritebackAudit = {
  job_id: string;
  status: string;
  row_id: string;
  report_url: string;
  fields: Record<string, string>;
  error_message: string;
  created_at: string;
  updated_at: string;
};

export type SpreadsheetWritebackAuditCounts = {
  by_status: Record<string, number>;
  total_count: number;
};

export type SpreadsheetWritebackAuditListResponse = {
  audits: SpreadsheetWritebackAudit[];
  total_count: number;
};

export type LarkSpreadsheetStatus = {
  configured: boolean;
  spreadsheet_id: string;
  sheet_id: string;
  lark_cli_timeout_seconds: number;
  connectivity_status: "not_checked" | "ok" | "failed";
  error_message: string;
};

export type ExperimentEvidence = {
  evidence_id: string;
  step_name: string;
  trial: number;
  model_name: string;
  model_provider: string;
  model_id: string;
  request_summary: {
    prompt_length?: number;
    has_image?: boolean;
    image_uri_scheme?: string;
    ablation_variant?: string;
    ablation_modalities?: string[];
  };
  latency_ms: number;
  response_parse_error: string;
  model_call_error_type: string;
  model_call_error_message: string;
  image_artifacts?: ImageArtifact[];
  artifacts?: EvidenceArtifact[];
  raw_output: string;
  judge: {
    score: number;
    reasons: string[];
    deltas?: JudgeDelta[];
  };
};

export async function debugFixtureCase(caseId: string): Promise<DebugReport> {
  const response = await fetch(`/api/cases/${caseId}/debug`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to debug case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}

export async function submitDebugJob(caseId: string, baselineTrials = 5): Promise<SubmittedDebugJob> {
  const params = new URLSearchParams({
    auto_run: "true",
    baseline_trials: String(baselineTrials)
  });
  const response = await fetch(`/api/cases/${caseId}/debug-jobs?${params.toString()}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to submit debug job for case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as SubmittedDebugJob;
}

export async function submitBatchDebugJobs(caseIds: string[]): Promise<BatchDebugJobResponse> {
  const response = await fetch("/api/debug-jobs/batch", {
    body: JSON.stringify({ case_ids: caseIds }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to submit batch debug jobs: ${response.status}`);
  }
  return (await response.json()) as BatchDebugJobResponse;
}

export async function fetchCases(hasRegions?: boolean, limit?: number, offset?: number): Promise<DebugCaseListResponse> {
  const params = new URLSearchParams();
  if (hasRegions) {
    params.set("has_regions", "true");
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/cases${query}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch imported cases: ${response.status}`);
  }
  return (await response.json()) as DebugCaseListResponse;
}

export async function fetchCaseDetail(caseId: string): Promise<DebugCaseDetail> {
  const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as DebugCaseDetail;
}

export async function importJsonlCases(jsonl: string, createJobs = true): Promise<JsonlImportResponse> {
  const response = await fetch("/api/imports/jsonl", {
    body: JSON.stringify({ jsonl, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to import JSONL cases: ${response.status}`);
  }
  return (await response.json()) as JsonlImportResponse;
}

export async function importCsvCases(csvText: string, createJobs = true): Promise<CsvImportResponse> {
  const response = await fetch("/api/imports/csv", {
    body: JSON.stringify({ csv_text: csvText, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to import CSV cases: ${response.status}`);
  }
  return (await response.json()) as CsvImportResponse;
}

export async function importSpreadsheetRows(
  rows: Array<Record<string, unknown>>,
  createJobs = true
): Promise<SpreadsheetRowImportResponse> {
  const response = await fetch("/api/imports/spreadsheet-rows", {
    body: JSON.stringify({ rows, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to import spreadsheet rows: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetRowImportResponse;
}

export async function fetchLarkSpreadsheetStatus(checkConnectivity = false): Promise<LarkSpreadsheetStatus> {
  const params = new URLSearchParams();
  if (checkConnectivity) {
    params.set("check_connectivity", "true");
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/spreadsheets/lark/status${query}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch Lark spreadsheet status: ${response.status}`);
  }
  return (await response.json()) as LarkSpreadsheetStatus;
}

export async function syncSpreadsheetRows(
  spreadsheetId: string,
  sheetId: string,
  createJobs = true,
  baselineTrials = 5
): Promise<SpreadsheetSyncResponse> {
  const response = await fetch("/api/spreadsheets/sync", {
    body: JSON.stringify({
      spreadsheet_id: spreadsheetId,
      sheet_id: sheetId,
      create_jobs: createJobs,
      baseline_trials: baselineTrials
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to sync spreadsheet rows: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetSyncResponse;
}

export async function fetchJobStatus(jobId: string): Promise<DebugJobStatus> {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch debug job ${jobId}: ${response.status}`);
  }
  return (await response.json()) as DebugJobStatus;
}

export async function fetchJobReport(jobId: string): Promise<DebugReport> {
  const response = await fetch(`/api/jobs/${jobId}/report`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job report ${jobId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}

export async function writeJobReportToSpreadsheet(
  jobId: string,
  reportUrl: string
): Promise<SpreadsheetWritebackResult> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback`, {
    body: JSON.stringify({ report_url: reportUrl }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to write job report ${jobId}: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackResult;
}

export async function updateRecommendedActionStatus(
  jobId: string,
  actionIndex: number,
  request: {
    status: RecommendedActionStatusValue;
    actor?: string;
    note?: string;
  }
): Promise<RecommendedActionStatus> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/recommended-actions/${actionIndex}/status`,
    {
      body: JSON.stringify({
        status: request.status,
        actor: request.actor ?? "",
        note: request.note ?? ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "PATCH"
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update recommended action ${actionIndex} for job ${jobId}: ${response.status}`);
  }
  return (await response.json()) as RecommendedActionStatus;
}

export async function fetchRecommendedActionStatuses(jobId: string): Promise<RecommendedActionStatusListResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/recommended-actions/statuses`);
  if (!response.ok) {
    throw new Error(`Failed to fetch recommended action statuses for job ${jobId}: ${response.status}`);
  }
  return (await response.json()) as RecommendedActionStatusListResponse;
}

export async function createRecommendedActionVerificationJob(
  jobId: string,
  actionIndex: number,
  request: {
    actor?: string;
    note?: string;
  }
): Promise<RecommendedActionVerificationResponse> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/recommended-actions/${actionIndex}/verification-jobs`,
    {
      body: JSON.stringify({
        actor: request.actor ?? "",
        note: request.note ?? ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to create recommended action verification job ${actionIndex} for ${jobId}: ${response.status}`);
  }
  return (await response.json()) as RecommendedActionVerificationResponse;
}

export async function fetchSpreadsheetWritebackAudit(jobId: string): Promise<SpreadsheetWritebackAudit> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback/audit`);
  if (!response.ok) {
    throw new Error(`Failed to fetch spreadsheet writeback audit ${jobId}: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackAudit;
}

export async function fetchSpreadsheetWritebackAuditSummary(): Promise<SpreadsheetWritebackAuditCounts> {
  const response = await fetch("/api/spreadsheets/writeback/audits/summary");
  if (!response.ok) {
    throw new Error(`Failed to fetch spreadsheet writeback audit summary: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackAuditCounts;
}

export async function fetchSpreadsheetWritebackAudits(
  status?: string,
  limit?: number,
  offset?: number
): Promise<SpreadsheetWritebackAuditListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/spreadsheets/writeback/audits${query}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch spreadsheet writeback audits: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackAuditListResponse;
}

export async function fetchDebugJobs(
  status?: string,
  limit?: number,
  offset?: number,
  sort?: string
): Promise<DebugJobListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  if (sort) {
    params.set("sort", sort);
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/jobs${query}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch debug jobs: ${response.status}`);
  }
  return (await response.json()) as DebugJobListResponse;
}

export async function fetchWorkerStatus(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/status");
  if (!response.ok) {
    throw new Error(`Failed to fetch worker status: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}

export async function fetchObservabilitySummary(): Promise<ObservabilitySummary> {
  const response = await fetch("/api/observability/summary");
  if (!response.ok) {
    throw new Error(`Failed to fetch observability summary: ${response.status}`);
  }
  return (await response.json()) as ObservabilitySummary;
}

export async function startWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/start", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to start worker: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}

export async function stopWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/stop", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to stop worker: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}

export async function fetchEvidenceDetail(
  caseId: string,
  evidenceId: string
): Promise<ExperimentEvidence> {
  const response = await fetch(`/api/cases/${caseId}/evidence/${encodeURIComponent(evidenceId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch evidence ${evidenceId}: ${response.status}`);
  }
  return (await response.json()) as ExperimentEvidence;
}

export async function fetchJobEvidenceDetail(
  jobId: string,
  evidenceId: string
): Promise<ExperimentEvidence> {
  const response = await fetch(`/api/jobs/${jobId}/evidence/${encodeURIComponent(evidenceId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job evidence ${evidenceId}: ${response.status}`);
  }
  return (await response.json()) as ExperimentEvidence;
}

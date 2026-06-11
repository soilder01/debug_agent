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
    evidence_ids: string[];
    image_artifact_ids?: string[];
  } | null;
  root_cause: {
    label: string;
    confidence: string;
    evidence_summary: string;
  };
  suggested_sheet_fields: Record<string, string>;
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
  region: {
    x: number;
    y: number;
    width: number;
    height: number;
    unit: string;
    label: string;
  } | null;
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
  };
  latency_ms: number;
  response_parse_error: string;
  model_call_error_type: string;
  model_call_error_message: string;
  image_artifacts?: ImageArtifact[];
  raw_output: string;
  judge: {
    score: number;
    reasons: string[];
  };
};

export async function debugFixtureCase(caseId: string): Promise<DebugReport> {
  const response = await fetch(`/api/cases/${caseId}/debug`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to debug case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}

export async function submitDebugJob(caseId: string): Promise<SubmittedDebugJob> {
  const response = await fetch(`/api/cases/${caseId}/debug-jobs?auto_run=true`, { method: "POST" });
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

export async function fetchJobStatus(jobId: string): Promise<DebugJobStatus> {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch debug job ${jobId}: ${response.status}`);
  }
  return (await response.json()) as DebugJobStatus;
}

export async function fetchDebugJobs(status?: string, limit?: number): Promise<DebugJobListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
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

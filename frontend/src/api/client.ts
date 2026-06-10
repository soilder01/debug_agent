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
  } | null;
  root_cause: {
    label: string;
    confidence: string;
    evidence_summary: string;
  };
  suggested_sheet_fields: Record<string, string>;
};

export type SubmittedDebugJob = {
  job_id: string;
  case_id: string;
  status: string;
  attempt_count?: number;
  error_message?: string | null;
  evidence_ids?: string[];
};

export type DebugJobStatus = {
  job_id: string;
  case_id: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  evidence_ids: string[];
};

export type BatchDebugJobResponse = {
  jobs: SubmittedDebugJob[];
  rejected_case_ids: string[];
};

export type WorkerStatus = {
  running: boolean;
  processed_count: number;
  error_count: number;
  last_error: string | null;
};

export type ExperimentEvidence = {
  evidence_id: string;
  step_name: string;
  trial: number;
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

export async function fetchJobStatus(jobId: string): Promise<DebugJobStatus> {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch debug job ${jobId}: ${response.status}`);
  }
  return (await response.json()) as DebugJobStatus;
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

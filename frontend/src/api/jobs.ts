import type {
  SubmittedDebugJob,
  DebugJobStatus,
  BatchDebugJobResponse,
  BatchDebugJobRequest,
  DebugBatchProgress,
  DebugBatchComparisonResponse,
  DebugBatchListResponse,
  DebugJobListResponse
} from "./types";

export async function submitDebugJob(caseId: string, baselineTrials = 5): Promise<SubmittedDebugJob> {
  const params = new URLSearchParams({
    auto_run: "true",
    baseline_trials: String(baselineTrials)
  });
  const response = await fetch(`/api/cases/${caseId}/debug-jobs?${params.toString()}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`提交样本 ${caseId} 的调试任务失败：${response.status}`);
  }
  return (await response.json()) as SubmittedDebugJob;
}


export async function submitBatchDebugJobs(request: string[] | BatchDebugJobRequest, maxConcurrency = 1): Promise<BatchDebugJobResponse> {
  const payload =
    Array.isArray(request)
      ? { case_ids: request, max_concurrency: maxConcurrency }
      : {
          case_ids: request.caseIds,
          max_concurrency: request.maxConcurrency ?? maxConcurrency,
          agent_model_config: request.agentModelConfig
        };
  const response = await fetch("/api/debug-jobs/batch", {
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`提交批量调试任务失败：${response.status}`);
  }
  return (await response.json()) as BatchDebugJobResponse;
}


export async function fetchDebugBatches(): Promise<DebugBatchListResponse> {
  const response = await fetch("/api/debug-batches");
  if (!response.ok) {
    throw new Error(`加载调试批次失败：${response.status}`);
  }
  return (await response.json()) as DebugBatchListResponse;
}


export async function fetchDebugBatch(batchId: string): Promise<DebugBatchProgress> {
  const response = await fetch(`/api/debug-batches/${encodeURIComponent(batchId)}`);
  if (!response.ok) {
    throw new Error(`加载调试批次 ${batchId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugBatchProgress;
}


export async function fetchDebugBatchComparison(batchIds: string[]): Promise<DebugBatchComparisonResponse> {
  const params = new URLSearchParams();
  if (batchIds.length > 0) {
    params.set("batch_ids", batchIds.join(","));
  }
  const query = params.toString();
  const response = await fetch(`/api/debug-batches/comparison${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`加载批次 A/B 对比失败：${response.status}`);
  }
  return (await response.json()) as DebugBatchComparisonResponse;
}


export async function updateDebugBatchStatus(
  batchId: string,
  action: "pause" | "resume" | "cancel"
): Promise<DebugBatchProgress> {
  const response = await fetch(`/api/debug-batches/${encodeURIComponent(batchId)}/${action}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`执行批次操作 ${action} 失败，批次 ${batchId}：${response.status}`);
  }
  return (await response.json()) as DebugBatchProgress;
}


export async function fetchJobStatus(jobId: string): Promise<DebugJobStatus> {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`加载调试任务 ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugJobStatus;
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
    throw new Error(`加载调试任务列表失败：${response.status}`);
  }
  return (await response.json()) as DebugJobListResponse;
}


export function debugJobExportUrl({
  jobIds = [],
  status,
  limit,
  sort
}: {
  jobIds?: string[];
  status?: string;
  limit?: number;
  sort?: string;
}): string {
  const params = new URLSearchParams();
  if (jobIds.length > 0) {
    params.set("job_ids", jobIds.join(","));
  }
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (sort) {
    params.set("sort", sort);
  }
  return `/api/exports/debug-jobs.zip?${params.toString()}`;
}

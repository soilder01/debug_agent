import type {
  ActionQueueResponse,
  DebugRunView,
  DebugReport,
  RecommendedActionStatusValue,
  RecommendedActionStatus,
  RecommendedActionVerificationResponse,
  StrategyFollowUpJobResponse,
  TargetedProbeJobResponse,
  AutoDebugClosureResult,
  AutoDebugClosureReportResponse,
  DebugRunStageListResponse,
  EvidenceLedgerResponse,
  HumanHandoffStatusValue,
  HumanHandoffStatus,
  StrategyFollowUpJobListResponse,
  TargetedProbeJobListResponse,
  HumanHandoffStatusListResponse,
  RecommendedActionStatusListResponse
} from "./types";

export async function fetchJobReport(jobId: string): Promise<DebugReport> {
  const response = await fetch(`/api/jobs/${jobId}/report`);
  if (!response.ok) {
    throw new Error(`加载任务报告 ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugReport;
}


export async function fetchDebugRunView(jobId: string): Promise<DebugRunView> {
  const response = await fetch(`/api/jobs/${jobId}/run-view`);
  if (!response.ok) {
    throw new Error(`加载 DebugRunView ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugRunView;
}


export async function fetchDebugRunStages(jobId: string): Promise<DebugRunStageListResponse> {
  const response = await fetch(`/api/jobs/${jobId}/run-stages`);
  if (!response.ok) {
    throw new Error(`加载 Debug Run 状态机 ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugRunStageListResponse;
}


export async function fetchEvidenceLedger(jobId: string): Promise<EvidenceLedgerResponse> {
  const response = await fetch(`/api/jobs/${jobId}/evidence-ledger`);
  if (!response.ok) {
    throw new Error(`加载证据账本 ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as EvidenceLedgerResponse;
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
    throw new Error(`更新任务 ${jobId} 的推荐操作 ${actionIndex} 失败：${response.status}`);
  }
  return (await response.json()) as RecommendedActionStatus;
}


export async function fetchRecommendedActionStatuses(jobId: string): Promise<RecommendedActionStatusListResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/recommended-actions/statuses`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的推荐操作状态失败：${response.status}`);
  }
  return (await response.json()) as RecommendedActionStatusListResponse;
}


export async function fetchActionQueue(jobId: string): Promise<ActionQueueResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/action-queue`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的 Action Queue 失败：${response.status}`);
  }
  return (await response.json()) as ActionQueueResponse;
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
    throw new Error(`创建任务 ${jobId} 的推荐操作 ${actionIndex} 验证任务失败：${response.status}`);
  }
  return (await response.json()) as RecommendedActionVerificationResponse;
}


export async function createStrategyFollowUpJob(
  jobId: string,
  stage: string,
  request: {
    actor?: string;
    note?: string;
  }
): Promise<StrategyFollowUpJobResponse> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/strategy-follow-ups/${encodeURIComponent(stage)}/debug-jobs`,
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
    throw new Error(`创建任务 ${jobId} 的策略跟进任务 ${stage} 失败：${response.status}`);
  }
  return (await response.json()) as StrategyFollowUpJobResponse;
}


export async function fetchStrategyFollowUpJobs(jobId: string): Promise<StrategyFollowUpJobListResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/strategy-follow-ups`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的策略跟进任务失败：${response.status}`);
  }
  return (await response.json()) as StrategyFollowUpJobListResponse;
}


export async function fetchTargetedProbeJobs(jobId: string): Promise<TargetedProbeJobListResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/targeted-probes`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的定向探测任务失败：${response.status}`);
  }
  return (await response.json()) as TargetedProbeJobListResponse;
}


export async function createTargetedProbeJob(
  jobId: string,
  targetId: string,
  request: {
    actor?: string;
    note?: string;
  }
): Promise<TargetedProbeJobResponse> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/targeted-probes/${encodeURIComponent(targetId)}/debug-jobs`,
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
    throw new Error(`创建任务 ${jobId} 的定向探测任务 ${targetId} 失败：${response.status}`);
  }
  return (await response.json()) as TargetedProbeJobResponse;
}


export async function runAutoDebugClosure(
  jobId: string,
  request: {
    actor?: string;
    note?: string;
    writeback?: boolean;
    report_url?: string;
    submitControlledProbes?: boolean;
  }
): Promise<AutoDebugClosureResult> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/auto-closure`, {
    body: JSON.stringify({
      actor: request.actor ?? "",
      note: request.note ?? "",
      writeback: request.writeback ?? false,
      report_url: request.report_url ?? "",
      submit_controlled_probes: request.submitControlledProbes ?? false
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`执行任务 ${jobId} 的自动闭环失败：${response.status}`);
  }
  return (await response.json()) as AutoDebugClosureResult;
}


export async function runAutoDebugClosureReport(
  jobId: string,
  request: {
    actor?: string;
    note?: string;
    writeback?: boolean;
    report_url?: string;
    submitControlledProbes?: boolean;
  }
): Promise<AutoDebugClosureReportResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/auto-closure/report`, {
    body: JSON.stringify({
      actor: request.actor ?? "",
      note: request.note ?? "",
      writeback: request.writeback ?? false,
      report_url: request.report_url ?? "",
      submit_controlled_probes: request.submitControlledProbes ?? false
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`生成任务 ${jobId} 的自动闭环报告失败：${response.status}`);
  }
  return (await response.json()) as AutoDebugClosureReportResponse;
}


export async function createFinalAttributionVerificationJob(
  jobId: string,
  targetId: string,
  request: {
    actor?: string;
    note?: string;
  }
): Promise<StrategyFollowUpJobResponse> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/final-attributions/${encodeURIComponent(targetId)}/verification-jobs`,
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
    throw new Error(`创建任务 ${jobId} 的最终归因验证任务 ${targetId} 失败：${response.status}`);
  }
  return (await response.json()) as StrategyFollowUpJobResponse;
}


export async function createFinalAttributionRecoveryJob(
  jobId: string,
  targetId: string,
  request: {
    actor?: string;
    note?: string;
  }
): Promise<StrategyFollowUpJobResponse> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/final-attribution-recoveries/${encodeURIComponent(targetId)}/debug-jobs`,
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
    throw new Error(`创建任务 ${jobId} 的最终归因恢复任务 ${targetId} 失败：${response.status}`);
  }
  return (await response.json()) as StrategyFollowUpJobResponse;
}


export async function updateHumanHandoffStatus(
  jobId: string,
  targetId: string,
  request: {
    status: HumanHandoffStatusValue;
    actor?: string;
    note?: string;
  }
): Promise<HumanHandoffStatus> {
  const response = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/human-handoffs/${encodeURIComponent(targetId)}/status`,
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
    throw new Error(`更新任务 ${jobId} 的人工接管 ${targetId} 失败：${response.status}`);
  }
  return (await response.json()) as HumanHandoffStatus;
}


export async function fetchHumanHandoffStatuses(jobId: string): Promise<HumanHandoffStatusListResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/human-handoffs/statuses`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的人工接管状态失败：${response.status}`);
  }
  return (await response.json()) as HumanHandoffStatusListResponse;
}

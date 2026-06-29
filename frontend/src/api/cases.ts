import type {
  DebugReport,
  DebugCaseListResponse,
  DebugCaseDetail,
  ExperimentEvidence
} from "./types";

export async function debugFixtureCase(caseId: string): Promise<DebugReport> {
  const response = await fetch(`/api/cases/${caseId}/debug`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`调试样本 ${caseId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugReport;
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
    throw new Error(`加载导入样本失败：${response.status}`);
  }
  return (await response.json()) as DebugCaseListResponse;
}


export async function fetchCaseDetail(caseId: string): Promise<DebugCaseDetail> {
  const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}`);
  if (!response.ok) {
    throw new Error(`加载样本 ${caseId} 失败：${response.status}`);
  }
  return (await response.json()) as DebugCaseDetail;
}


export async function fetchEvidenceDetail(
  caseId: string,
  evidenceId: string
): Promise<ExperimentEvidence> {
  const response = await fetch(`/api/cases/${caseId}/evidence/${encodeURIComponent(evidenceId)}`);
  if (!response.ok) {
    throw new Error(`加载证据 ${evidenceId} 失败：${response.status}`);
  }
  return (await response.json()) as ExperimentEvidence;
}


export async function fetchJobEvidenceDetail(
  jobId: string,
  evidenceId: string
): Promise<ExperimentEvidence> {
  const response = await fetch(`/api/jobs/${jobId}/evidence/${encodeURIComponent(evidenceId)}`);
  if (!response.ok) {
    throw new Error(`加载任务证据 ${evidenceId} 失败：${response.status}`);
  }
  return (await response.json()) as ExperimentEvidence;
}

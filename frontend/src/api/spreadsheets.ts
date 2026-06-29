import { buildHttpErrorMessage } from "./http";
import type {
  SpreadsheetSyncResponse,
  SpreadsheetRerunResponse,
  SpreadsheetWritebackResult,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackAuditCounts,
  SpreadsheetWritebackAuditListResponse,
  LarkWriteConfirmation,
  LarkSpreadsheetStatus
} from "./types";

export async function fetchLarkSpreadsheetStatus(
  checkConnectivity = false,
  reference?: {
    spreadsheetUrl?: string;
    spreadsheetId?: string;
    sheetId?: string;
  }
): Promise<LarkSpreadsheetStatus> {
  const params = new URLSearchParams();
  if (checkConnectivity) {
    params.set("check_connectivity", "true");
  }
  if (reference?.spreadsheetUrl) {
    params.set("spreadsheet_url", reference.spreadsheetUrl);
  }
  if (reference?.spreadsheetId) {
    params.set("spreadsheet_id", reference.spreadsheetId);
  }
  if (reference?.sheetId) {
    params.set("sheet_id", reference.sheetId);
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/spreadsheets/lark/status${query}`);
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("加载飞书表格状态失败", response));
  }
  return (await response.json()) as LarkSpreadsheetStatus;
}


export async function syncSpreadsheetRows(
  spreadsheetId: string,
  sheetId: string,
  createJobs = true,
  baselineTrials = 5,
  spreadsheetUrl = ""
): Promise<SpreadsheetSyncResponse> {
  const response = await fetch("/api/spreadsheets/sync", {
    body: JSON.stringify({
      spreadsheet_url: spreadsheetUrl,
      spreadsheet_id: spreadsheetId,
      sheet_id: sheetId,
      create_jobs: createJobs,
      baseline_trials: baselineTrials
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("同步飞书表格行失败", response));
  }
  return (await response.json()) as SpreadsheetSyncResponse;
}


export async function rerunSpreadsheetRows(request: {
  spreadsheetId: string;
  sheetId: string;
  spreadsheetUrl?: string;
  rowIds: string[];
  baselineTrials?: number;
  autoRun?: boolean;
  autoClosure?: boolean;
  submitControlledProbes?: boolean;
  writeback?: boolean;
}): Promise<SpreadsheetRerunResponse> {
  const response = await fetch("/api/spreadsheets/rerun", {
    body: JSON.stringify({
      spreadsheet_url: request.spreadsheetUrl ?? "",
      spreadsheet_id: request.spreadsheetId,
      sheet_id: request.sheetId,
      row_ids: request.rowIds,
      baseline_trials: request.baselineTrials ?? 5,
      auto_run: request.autoRun ?? true,
      auto_closure: request.autoClosure ?? false,
      submit_controlled_probes: request.submitControlledProbes ?? false,
      writeback: request.writeback ?? false
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("重跑飞书表格行失败", response));
  }
  return (await response.json()) as SpreadsheetRerunResponse;
}


export async function writeJobReportToSpreadsheet(
  jobId: string,
  reportUrl: string,
  reference?: {
    spreadsheetUrl?: string;
    spreadsheetId?: string;
    sheetId?: string;
    requireConfirmation?: boolean;
    confirmationId?: string;
    actor?: string;
    note?: string;
  }
): Promise<SpreadsheetWritebackResult> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback`, {
    body: JSON.stringify({
      report_url: reportUrl,
      spreadsheet_url: reference?.spreadsheetUrl ?? "",
      spreadsheet_id: reference?.spreadsheetId ?? "",
      sheet_id: reference?.sheetId ?? "",
      require_confirmation: reference?.requireConfirmation ?? false,
      confirmation_id: reference?.confirmationId ?? "",
      actor: reference?.actor ?? "",
      note: reference?.note ?? ""
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`写回任务报告 ${jobId} 失败：${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackResult;
}


export async function createJobReportWritebackConfirmation(
  jobId: string,
  request: {
    reportUrl?: string;
    spreadsheetUrl?: string;
    spreadsheetId?: string;
    sheetId?: string;
    actor?: string;
    note?: string;
  }
): Promise<LarkWriteConfirmation> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback/confirmation`, {
    body: JSON.stringify({
      report_url: request.reportUrl ?? "",
      spreadsheet_url: request.spreadsheetUrl ?? "",
      spreadsheet_id: request.spreadsheetId ?? "",
      sheet_id: request.sheetId ?? "",
      actor: request.actor ?? "",
      note: request.note ?? ""
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`创建任务 ${jobId} 的 Lark 写回确认失败：${response.status}`);
  }
  return (await response.json()) as LarkWriteConfirmation;
}


export async function confirmLarkWriteConfirmation(
  confirmationId: string,
  request: { actor?: string; note?: string } = {}
): Promise<LarkWriteConfirmation> {
  const response = await fetch(`/api/lark/write-confirmations/${encodeURIComponent(confirmationId)}/confirm`, {
    body: JSON.stringify({
      actor: request.actor ?? "",
      note: request.note ?? ""
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`确认 Lark 写回风险失败：${response.status}`);
  }
  return (await response.json()) as LarkWriteConfirmation;
}


export async function fetchSpreadsheetWritebackAudit(jobId: string): Promise<SpreadsheetWritebackAudit> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback/audit`);
  if (!response.ok) {
    throw new Error(`加载任务 ${jobId} 的表格回写审计失败：${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackAudit;
}


export async function fetchSpreadsheetWritebackAuditSummary(): Promise<SpreadsheetWritebackAuditCounts> {
  const response = await fetch("/api/spreadsheets/writeback/audits/summary");
  if (!response.ok) {
    throw new Error(`加载表格回写审计概览失败：${response.status}`);
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
    throw new Error(`加载表格回写审计列表失败：${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackAuditListResponse;
}

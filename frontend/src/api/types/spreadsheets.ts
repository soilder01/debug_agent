import type { AutoDebugClosureResult, DebugBatchProgress, SubmittedDebugJob } from "./debug";

export type SpreadsheetImportedRowResponse = {
  sheet_row_id: string;
  case_id: string;
};

export type SpreadsheetRejectedRow = {
  row_index: number;
  sheet_row_id: string;
  error_message: string;
};

export type SpreadsheetAutoClosureReport = {
  job_id: string;
  case_id: string;
  closure: AutoDebugClosureResult;
  report_artifact_url: string;
  writeback_status: string;
};

export type SpreadsheetRowImportResponse = {
  imported_case_ids: string[];
  imported_rows: SpreadsheetImportedRowResponse[];
  jobs: SubmittedDebugJob[];
  rejected_rows: SpreadsheetRejectedRow[];
  auto_closure_reports?: SpreadsheetAutoClosureReport[];
};

export type SpreadsheetSyncResponse = SpreadsheetRowImportResponse;

export type SpreadsheetRerunResponse = Omit<SpreadsheetRowImportResponse, "auto_closure_reports"> & {
  skipped_row_ids: string[];
  batch?: DebugBatchProgress | null;
  auto_closure_reports: SpreadsheetAutoClosureReport[];
};

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

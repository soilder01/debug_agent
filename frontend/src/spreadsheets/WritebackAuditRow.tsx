import type { SpreadsheetWritebackAudit } from "../api/client";

type WritebackAuditRowProps = {
  audit: SpreadsheetWritebackAudit;
  onOpenJob: (jobId: string) => void;
  onRetry: (audit: SpreadsheetWritebackAudit) => void;
};

export function WritebackAuditRow({ audit, onOpenJob, onRetry }: WritebackAuditRowProps) {
  return (
    <li>
      {audit.job_id}：{audit.status}｜row {audit.row_id || "无"}｜{audit.error_message || "无错误"}
      <span>updated {audit.updated_at}</span>
      <span>Retry eligibility：{audit.status === "failed" ? "available" : "unavailable"}</span>
      <span>Retry reason：{writebackRetryReason(audit.status, audit.error_message)}</span>
      <span>Writeback audit fields：{Object.keys(audit.fields).length}</span>
      {Object.entries(audit.fields).map(([key, value]) => (
        <span key={key}>
          Writeback audit field：{key}={value}
        </span>
      ))}
      <button type="button" onClick={() => onOpenJob(audit.job_id)}>
        Open audit job {audit.job_id}
      </button>
      {audit.status === "failed" ? (
        <button type="button" onClick={() => onRetry(audit)}>
          Retry writeback {audit.job_id}
        </button>
      ) : null}
      {audit.report_url ? (
        <a href={audit.report_url} target="_blank" rel="noreferrer">
          Open report {audit.job_id}
        </a>
      ) : null}
    </li>
  );
}

function writebackRetryReason(status: string, errorMessage: string): string {
  if (status === "failed") {
    return "last writeback failed";
  }
  if (status === "succeeded") {
    return "already succeeded";
  }
  if (errorMessage) {
    return errorMessage;
  }
  return "missing prerequisites";
}

import type { SpreadsheetWritebackAudit } from "../api/client";
import { ActionRow, StatusBadge } from "../ui/ProductPrimitives";
import { NativeWritebackFields } from "./NativeWritebackFields";
import { canRetryWritebackAudit, writebackRetryReason } from "./writebackAuditPolicy";

type WritebackAuditRowProps = {
  audit: SpreadsheetWritebackAudit;
  onOpenJob: (jobId: string) => void;
  onRetry: (audit: SpreadsheetWritebackAudit) => void;
};

export function WritebackAuditRow({ audit, onOpenJob, onRetry }: WritebackAuditRowProps) {
  const isRetryable = canRetryWritebackAudit(audit.status);

  return (
    <li className="writeback-audit-row">
      {audit.job_id}：{audit.status}｜row {audit.row_id || "无"}｜{audit.error_message || "无错误"}
      <StatusBadge tone={writebackTone(audit.status)}>{audit.status}</StatusBadge>
      <span>updated {audit.updated_at}</span>
      <span>Retry eligibility：{isRetryable ? "available" : "unavailable"}</span>
      <span>Retry reason：{writebackRetryReason(audit.status, audit.error_message)}</span>
      <span>Writeback audit fields：{Object.keys(audit.fields).length}</span>
      <NativeWritebackFields fields={audit.fields} />
      {Object.entries(audit.fields).map(([key, value]) => (
        <span key={key}>
          Writeback audit field：{key}={value}
        </span>
      ))}
      <ActionRow label="Writeback audit row actions">
        <button type="button" onClick={() => onOpenJob(audit.job_id)}>
          Open audit job {audit.job_id}
        </button>
        {isRetryable ? (
          <button type="button" onClick={() => onRetry(audit)}>
            Retry writeback {audit.job_id}
          </button>
        ) : null}
      </ActionRow>
      {audit.report_url ? (
        <a href={audit.report_url} target="_blank" rel="noreferrer">
          Open report {audit.job_id}
        </a>
      ) : null}
    </li>
  );
}

function writebackTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "skipped") {
    return "warning";
  }
  if (status === "succeeded") {
    return "success";
  }
  return "neutral";
}

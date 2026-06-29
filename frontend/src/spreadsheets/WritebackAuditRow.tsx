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
  const statusText = writebackStatusLabel(audit.status);

  return (
    <li className="writeback-audit-row">
      {audit.job_id}：{statusText}｜行 {audit.row_id || "无"}｜{audit.error_message || "无错误"}
      <StatusBadge tone={writebackTone(audit.status)}>{statusText}</StatusBadge>
      <span>更新时间：{audit.updated_at}</span>
      <span>可重试：{isRetryable ? "是" : "否"}</span>
      <span>重试原因：{writebackRetryReason(audit.status, audit.error_message)}</span>
      <span>写回字段数：{Object.keys(audit.fields).length}</span>
      <NativeWritebackFields fields={audit.fields} />
      {Object.entries(audit.fields).map(([key, value]) => (
        <span key={key}>
          写回字段：{key}={value}
        </span>
      ))}
      <ActionRow label="审计行操作">
        <button type="button" onClick={() => onOpenJob(audit.job_id)}>
          打开任务 {audit.job_id}
        </button>
        {isRetryable ? (
          <button type="button" onClick={() => onRetry(audit)}>
            重试写回 {audit.job_id}
          </button>
        ) : null}
      </ActionRow>
      {audit.report_url ? (
        <a href={audit.report_url} target="_blank" rel="noreferrer">
          打开报告 {audit.job_id}
        </a>
      ) : null}
    </li>
  );
}

function writebackStatusLabel(status: string): string {
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  if (status === "succeeded") {
    return "成功";
  }
  return status || "未知";
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

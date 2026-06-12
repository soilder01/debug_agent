import type { DebugJobStatus, SubmittedDebugJob } from "../api/client";

type JobStatusPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  onSelectEvidence?: (evidenceId: string) => void;
  onLoadReport?: () => void;
};

export function JobStatusPanel({ job, onSelectEvidence, onLoadReport }: JobStatusPanelProps) {
  const attemptCount = job.attempt_count ?? 0;
  const maxAttempts = job.max_attempts ?? 0;
  const remainingAttempts = job.remaining_attempts ?? 0;
  const willRetry = job.will_retry ?? false;
  const retryRecommendation = job.retry_recommendation ?? "unknown";
  const retryRecommendationDetail =
    "retry_recommendation_detail" in job ? job.retry_recommendation_detail : null;
  const errorMessage = job.error_message ?? "";
  const evidenceIds = job.evidence_ids ?? [];
  const evidenceCount = evidenceIds.length;
  const evidenceErrorCounts = "evidence_error_counts" in job ? job.evidence_error_counts : null;
  const spreadsheetWritebackAudit =
    "spreadsheet_writeback_audit" in job ? job.spreadsheet_writeback_audit : null;
  return (
    <section>
      <h2>Job Status</h2>
      <p>Job ID：{job.job_id}</p>
      <p>样本 ID：{job.case_id}</p>
      <p>状态：{job.status}</p>
      {job.created_at ? <p title={job.created_at}>创建时间：{formatJobTimestamp(job.created_at)}</p> : null}
      {job.updated_at ? <p title={job.updated_at}>更新时间：{formatJobTimestamp(job.updated_at)}</p> : null}
      <p>尝试次数：{attemptCount}</p>
      <p>最大尝试：{maxAttempts}</p>
      <p>剩余尝试：{remainingAttempts}</p>
      <p>将会重试：{String(willRetry)}</p>
      <p>重试建议：{retryRecommendationDetail?.label ?? retryRecommendation}</p>
      {retryRecommendationDetail ? <p>建议动作：{retryRecommendationDetail.action}</p> : null}
      {onLoadReport ? (
        <button type="button" onClick={onLoadReport}>
          Load persisted report
        </button>
      ) : null}
      <p>证据数：{evidenceCount}</p>
      {evidenceErrorCounts ? (
        <>
          <p>失败判分：{evidenceErrorCounts.failed_judgements}</p>
          <p>解析错误：{evidenceErrorCounts.response_parse_errors}</p>
          <p>模型调用错误：{evidenceErrorCounts.model_call_errors}</p>
        </>
      ) : null}
      {spreadsheetWritebackAudit ? (
        <>
          <p>写回状态：{spreadsheetWritebackAudit.status}</p>
          <p>写回行：{spreadsheetWritebackAudit.row_id}</p>
          {spreadsheetWritebackAudit.error_message ? (
            <p role="alert">写回错误：{spreadsheetWritebackAudit.error_message}</p>
          ) : null}
        </>
      ) : null}
      {evidenceIds.length > 0 ? (
        <ul aria-label="Job evidence ids">
          {evidenceIds.map((evidenceId) => (
            <li key={evidenceId}>
              <button type="button" onClick={() => onSelectEvidence?.(evidenceId)}>
                View evidence {evidenceId}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {errorMessage ? <p role="alert">错误：{errorMessage}</p> : null}
    </section>
  );
}

function formatJobTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())} ${padDatePart(
    date.getHours()
  )}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`;
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

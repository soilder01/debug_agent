import type { DebugJobStatus, SubmittedDebugJob } from "../api/client";

type JobStatusPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  onSelectEvidence?: (evidenceId: string) => void;
};

export function JobStatusPanel({ job, onSelectEvidence }: JobStatusPanelProps) {
  const attemptCount = job.attempt_count ?? 0;
  const errorMessage = job.error_message ?? "";
  const evidenceIds = job.evidence_ids ?? [];
  const evidenceCount = evidenceIds.length;
  const evidenceErrorCounts = "evidence_error_counts" in job ? job.evidence_error_counts : null;
  return (
    <section>
      <h2>Job Status</h2>
      <p>Job ID：{job.job_id}</p>
      <p>样本 ID：{job.case_id}</p>
      <p>状态：{job.status}</p>
      <p>尝试次数：{attemptCount}</p>
      <p>证据数：{evidenceCount}</p>
      {evidenceErrorCounts ? (
        <>
          <p>失败判分：{evidenceErrorCounts.failed_judgements}</p>
          <p>解析错误：{evidenceErrorCounts.response_parse_errors}</p>
          <p>模型调用错误：{evidenceErrorCounts.model_call_errors}</p>
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

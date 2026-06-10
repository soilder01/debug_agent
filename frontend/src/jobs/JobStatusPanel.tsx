import type { DebugJobStatus, SubmittedDebugJob } from "../api/client";

type JobStatusPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
};

export function JobStatusPanel({ job }: JobStatusPanelProps) {
  const attemptCount = job.attempt_count ?? 0;
  const errorMessage = job.error_message ?? "";
  return (
    <section>
      <h2>Job Status</h2>
      <p>Job ID：{job.job_id}</p>
      <p>样本 ID：{job.case_id}</p>
      <p>状态：{job.status}</p>
      <p>尝试次数：{attemptCount}</p>
      {errorMessage ? <p role="alert">错误：{errorMessage}</p> : null}
    </section>
  );
}

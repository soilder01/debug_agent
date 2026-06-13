import type { DebugJobStatus, SubmittedDebugJob } from "../api/client";

type BatchJob = DebugJobStatus | SubmittedDebugJob;

type BatchJobListPanelProps = {
  jobs: BatchJob[];
  summaryLabel: string;
  totalCount: number;
  unloadedCount: number;
  rejectedCaseIds: string[];
  completedCount: number;
  onStartWorker: () => void;
  onLoadMore: () => void;
  onOpenJob: (job: BatchJob) => void;
  onSelectEvidence: (jobId: string, evidenceId: string) => void;
};

export function BatchJobListPanel({
  jobs,
  summaryLabel,
  totalCount,
  unloadedCount,
  rejectedCaseIds,
  completedCount,
  onStartWorker,
  onLoadMore,
  onOpenJob,
  onSelectEvidence
}: BatchJobListPanelProps) {
  return (
    <>
      <p>{summaryLabel}：{jobs.length}</p>
      <p>总任务：{totalCount}</p>
      <p>未加载：{unloadedCount}</p>
      <p>拒绝：{rejectedCaseIds.join(", ") || "无"}</p>
      <p>
        批量进度：{completedCount}/{jobs.length}
      </p>
      <button type="button" onClick={onStartWorker}>
        Start worker for batch
      </button>
      {unloadedCount > 0 ? (
        <button type="button" onClick={onLoadMore}>
          Load more debug jobs
        </button>
      ) : null}
      {jobs.length > 0 ? (
        <ul aria-label="Batch job statuses">
          {jobs.map((job) => (
            <li key={job.job_id}>
              <span>{job.job_id}：{job.status}</span>
              {job.created_at ? (
                <span title={job.created_at}>
                  {" "}
                  {job.job_id} 创建：{formatJobTimestamp(job.created_at)}
                </span>
              ) : null}
              {job.updated_at ? (
                <span title={job.updated_at}>
                  {" "}
                  {job.job_id} 更新：{formatJobTimestamp(job.updated_at)}
                </span>
              ) : null}
              {job.error_message ? <span> {job.job_id} 错误：{job.error_message}</span> : null}
              {job.retry_recommendation_detail ? (
                <>
                  <span> {job.job_id} 建议：{job.retry_recommendation_detail.label}</span>
                  <span> {job.job_id} 级别：{job.retry_recommendation_detail.severity}</span>
                </>
              ) : null}
              <button type="button" onClick={() => onOpenJob(job)}>
                Open job {job.job_id}
              </button>
              {job.evidence_ids?.map((evidenceId) => (
                <button key={evidenceId} type="button" onClick={() => onSelectEvidence(job.job_id, evidenceId)}>
                  Open evidence {evidenceId} for job {job.job_id}
                </button>
              ))}
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

function formatJobTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return (
    [date.getFullYear(), padDatePart(date.getMonth() + 1), padDatePart(date.getDate())].join("-") +
    ` ${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`
  );
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

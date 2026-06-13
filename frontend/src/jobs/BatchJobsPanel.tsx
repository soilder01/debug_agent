import type { BatchDebugJobResponse, DebugJobStatus, SubmittedDebugJob } from "../api/client";
import { BatchJobControlsPanel } from "./BatchJobControlsPanel";
import { BatchJobListPanel } from "./BatchJobListPanel";

type BatchJob = DebugJobStatus | SubmittedDebugJob;

type BatchJobsPanelProps = {
  caseIds: string;
  batchResult: BatchDebugJobResponse | null;
  jobs: BatchJob[];
  summaryLabel: string;
  totalCount: number;
  unloadedCount: number;
  completedCount: number;
  onCaseIdsChange: (value: string) => void;
  onSubmit: () => void;
  onLoadJobs: (status?: string, sort?: string) => void;
  onStartWorker: () => void;
  onLoadMore: () => void;
  onOpenJob: (job: BatchJob) => void;
  onSelectEvidence: (jobId: string, evidenceId: string) => void;
};

export function BatchJobsPanel({
  caseIds,
  batchResult,
  jobs,
  summaryLabel,
  totalCount,
  unloadedCount,
  completedCount,
  onCaseIdsChange,
  onSubmit,
  onLoadJobs,
  onStartWorker,
  onLoadMore,
  onOpenJob,
  onSelectEvidence
}: BatchJobsPanelProps) {
  return (
    <section>
      <BatchJobControlsPanel
        caseIds={caseIds}
        onCaseIdsChange={onCaseIdsChange}
        onSubmit={onSubmit}
        onLoadJobs={onLoadJobs}
      />
      {batchResult ? (
        <BatchJobListPanel
          jobs={jobs}
          summaryLabel={summaryLabel}
          totalCount={totalCount}
          unloadedCount={unloadedCount}
          rejectedCaseIds={batchResult.rejected_case_ids}
          completedCount={completedCount}
          onStartWorker={onStartWorker}
          onLoadMore={onLoadMore}
          onOpenJob={onOpenJob}
          onSelectEvidence={onSelectEvidence}
        />
      ) : null}
    </section>
  );
}

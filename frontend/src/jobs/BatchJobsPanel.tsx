import type { BatchDebugJobResponse, DebugJobStatus, SubmittedDebugJob } from "../api/client";
import { ProductSurface } from "../ui/ProductPrimitives";
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
    <ProductSurface
      title="Batch Jobs"
      eyebrow="Queue"
      description="Submit case batches, inspect queued jobs, and start background processing."
      className="batch-jobs-panel"
    >
      <BatchJobControlsPanel
        caseIds={caseIds}
        onCaseIdsChange={onCaseIdsChange}
        onSubmit={onSubmit}
        onLoadJobs={onLoadJobs}
        showHeading={false}
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
    </ProductSurface>
  );
}

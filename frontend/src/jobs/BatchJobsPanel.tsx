import type {
  BatchDebugJobResponse,
  DebugBatchProgress,
  DebugJobStatus,
  SubmittedDebugJob
} from "../api/client";
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
  batchProgress?: DebugBatchProgress | null;
  batchHistory?: DebugBatchProgress[];
  exportHref?: string;
  failedExportHref?: string;
  newestExportHref?: string;
  onCaseIdsChange: (value: string) => void;
  onSubmit: () => void;
  onLoadJobs: (status?: string, sort?: string) => void;
  onStartWorker: () => void;
  onPauseBatch?: () => void;
  onResumeBatch?: () => void;
  onCancelBatch?: () => void;
  onLoadBatches?: () => void;
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
  batchProgress,
  batchHistory,
  exportHref,
  failedExportHref,
  newestExportHref,
  onCaseIdsChange,
  onSubmit,
  onLoadJobs,
  onStartWorker,
  onPauseBatch,
  onResumeBatch,
  onCancelBatch,
  onLoadBatches,
  onLoadMore,
  onOpenJob,
  onSelectEvidence
}: BatchJobsPanelProps) {
  return (
    <ProductSurface
      title="调查工作台"
      eyebrow="执行台"
      description="这里执行已导入样本的 debug；还没有样本时，先去数据导入或回写同步。"
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
          batchProgress={batchProgress}
          batchHistory={batchHistory}
          exportHref={exportHref}
          failedExportHref={failedExportHref}
          newestExportHref={newestExportHref}
          onStartWorker={onStartWorker}
          onPauseBatch={onPauseBatch}
          onResumeBatch={onResumeBatch}
          onCancelBatch={onCancelBatch}
          onLoadBatches={onLoadBatches}
          onLoadMore={onLoadMore}
          onOpenJob={onOpenJob}
          onSelectEvidence={onSelectEvidence}
        />
      ) : null}
    </ProductSurface>
  );
}

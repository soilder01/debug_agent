import type { DebugCaseDetail, DebugCaseSummary } from "../api/client";
import { ActionRow, EmptyState, ProductSurface } from "../ui/ProductPrimitives";
import { ImportedCaseDetailPanel } from "./ImportedCaseDetailPanel";
import { ImportedCaseListPanel } from "./ImportedCaseListPanel";

type ImportedCasesPanelProps = {
  cases: DebugCaseSummary[];
  totalCount: number;
  effectiveCount: number;
  unloadedCount: number;
  selectedCaseDetail: DebugCaseDetail | null;
  onLoadImportedCases: () => void;
  onLoadWithRegions: () => void;
  onLoadAll: () => void;
  onLoadMore: () => void;
  onUseForBatch: () => void;
  onViewCaseDetail: (caseId: string) => void;
  onCreateDebugJob: (caseId: string) => void;
};

export function ImportedCasesPanel({
  cases,
  totalCount,
  effectiveCount,
  unloadedCount,
  selectedCaseDetail,
  onLoadImportedCases,
  onLoadWithRegions,
  onLoadAll,
  onLoadMore,
  onUseForBatch,
  onViewCaseDetail,
  onCreateDebugJob
}: ImportedCasesPanelProps) {
  return (
    <ProductSurface
      title="导入样本"
      eyebrow="队列"
      description="先加载导入样本，再启动定向 debug 任务。"
      className="case-queue"
    >
      <ActionRow label="导入样本操作">
        <button type="button" aria-label="加载导入样本" onClick={onLoadImportedCases}>
          加载案件
        </button>
      </ActionRow>
      {cases.length > 0 ? (
        <>
          <ImportedCaseListPanel
            cases={cases}
            totalCount={totalCount}
            effectiveCount={effectiveCount}
            unloadedCount={unloadedCount}
            onLoadWithRegions={onLoadWithRegions}
            onLoadAll={onLoadAll}
            onLoadMore={onLoadMore}
            onUseForBatch={onUseForBatch}
            onViewCaseDetail={onViewCaseDetail}
          />
          {selectedCaseDetail ? (
            <ImportedCaseDetailPanel caseDetail={selectedCaseDetail} onCreateDebugJob={onCreateDebugJob} />
          ) : null}
        </>
      ) : (
        <EmptyState title="尚未加载导入样本" description="从本地导入或飞书表格同步加载案件数据。" />
      )}
    </ProductSurface>
  );
}

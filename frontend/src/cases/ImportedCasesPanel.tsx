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
      title="Imported Cases"
      eyebrow="Queue"
      description="Load imported cases before starting targeted debug jobs."
      className="case-queue"
    >
      <ActionRow label="Imported case actions">
        <button type="button" onClick={onLoadImportedCases}>
          Load imported cases
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
        <EmptyState title="No imported cases loaded" description="Load cases from local imports or spreadsheet sync." />
      )}
    </ProductSurface>
  );
}

import type { DebugCaseDetail, DebugCaseSummary } from "../api/client";
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
    <section>
      <h2>Imported Cases</h2>
      <button type="button" onClick={onLoadImportedCases}>
        Load imported cases
      </button>
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
      ) : null}
    </section>
  );
}

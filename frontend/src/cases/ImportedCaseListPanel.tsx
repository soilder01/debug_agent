import type { DebugCaseSummary } from "../api/client";

type ImportedCaseListPanelProps = {
  cases: DebugCaseSummary[];
  totalCount: number;
  effectiveCount: number;
  unloadedCount: number;
  onLoadWithRegions: () => void;
  onLoadAll: () => void;
  onLoadMore: () => void;
  onUseForBatch: () => void;
  onViewCaseDetail: (caseId: string) => void;
};

export function ImportedCaseListPanel({
  cases,
  totalCount,
  effectiveCount,
  unloadedCount,
  onLoadWithRegions,
  onLoadAll,
  onLoadMore,
  onUseForBatch,
  onViewCaseDetail
}: ImportedCaseListPanelProps) {
  return (
    <>
      <p>已导入样本：{totalCount}</p>
      <p>
        已显示样本：{cases.length}/{effectiveCount}
      </p>
      <p>未加载样本：{unloadedCount}</p>
      <button type="button" onClick={onLoadWithRegions}>
        Only cases with regions
      </button>
      <button type="button" onClick={onLoadAll}>
        Show all imported cases
      </button>
      {unloadedCount > 0 ? (
        <button type="button" onClick={onLoadMore}>
          Load more imported cases
        </button>
      ) : null}
      <button type="button" onClick={onUseForBatch}>
        Use imported cases for batch
      </button>
      <ul aria-label="Imported case summaries">
        {cases.map((caseSummary) => (
          <li key={caseSummary.case_id}>
            {caseSummary.case_id}｜avg_score {caseSummary.avg_score}｜regions {caseSummary.box_region_count ?? 0}｜
            {caseSummary.debug_status || "未标记"}｜{caseSummary.root_cause || "未归因"}
            <button type="button" onClick={() => onViewCaseDetail(caseSummary.case_id)}>
              View case detail {caseSummary.case_id}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

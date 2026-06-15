import type { DebugCaseSummary } from "../api/client";
import { ActionRow, MetricStrip } from "../ui/ProductPrimitives";

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
  const safeTotalCount = Number.isFinite(totalCount) ? totalCount : cases.length;
  const safeEffectiveCount = Number.isFinite(effectiveCount) ? effectiveCount : cases.length;
  const safeUnloadedCount = Number.isFinite(unloadedCount) ? unloadedCount : 0;

  return (
    <>
      <MetricStrip
        label="Imported case queue metrics"
        metrics={[
          { label: "Imported", value: safeTotalCount, helper: "All loaded case rows" },
          { label: "Displayed", value: `${cases.length}/${safeEffectiveCount}`, helper: "Current filtered window" },
          { label: "Unloaded", value: safeUnloadedCount, helper: "Available for pagination" },
          {
            label: "Regions",
            value: cases.reduce((total, caseSummary) => total + (caseSummary.box_region_count ?? 0), 0),
            helper: "Targetable boxes"
          }
        ]}
      />
      <p>已导入样本：{safeTotalCount}</p>
      <p>
        已显示样本：{cases.length}/{safeEffectiveCount}
      </p>
      <p>未加载样本：{safeUnloadedCount}</p>
      <ActionRow label="Case queue actions">
        <button type="button" onClick={onLoadWithRegions}>
          Only cases with regions
        </button>
        <button type="button" onClick={onLoadAll}>
          Show all imported cases
        </button>
        {safeUnloadedCount > 0 ? (
          <button type="button" onClick={onLoadMore}>
            Load more imported cases
          </button>
        ) : null}
        <button type="button" onClick={onUseForBatch}>
          Use imported cases for batch
        </button>
      </ActionRow>
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

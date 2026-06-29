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
        label="导入样本队列指标"
        metrics={[
          { label: "已导入", value: safeTotalCount, helper: "已加载样本行" },
          { label: "已显示", value: `${cases.length}/${safeEffectiveCount}`, helper: "当前筛选窗口" },
          { label: "未加载", value: safeUnloadedCount, helper: "可继续分页" },
          {
            label: "区域",
            value: cases.reduce((total, caseSummary) => total + (caseSummary.box_region_count ?? 0), 0),
            helper: "可定向框选区域"
          }
        ]}
      />
      <p>已导入样本：{safeTotalCount}</p>
      <p>
        已显示样本：{cases.length}/{safeEffectiveCount}
      </p>
      <p>未加载样本：{safeUnloadedCount}</p>
      <ActionRow label="样本队列操作">
        <button type="button" onClick={onLoadWithRegions}>
          只看有区域的样本
        </button>
        <button type="button" onClick={onLoadAll}>
          显示全部导入样本
        </button>
        {safeUnloadedCount > 0 ? (
          <button type="button" onClick={onLoadMore}>
            加载更多导入样本
          </button>
        ) : null}
        <button type="button" onClick={onUseForBatch}>
          用导入样本创建批次
        </button>
      </ActionRow>
      <ul aria-label="导入样本摘要">
        {cases.map((caseSummary) => (
          <li key={caseSummary.case_id}>
            {caseSummary.case_id}｜平均分 {caseSummary.avg_score}｜区域 {caseSummary.box_region_count ?? 0}｜
            {caseSummary.debug_status || "未标记"}｜{caseSummary.root_cause || "未归因"}
            <button type="button" onClick={() => onViewCaseDetail(caseSummary.case_id)}>
              查看样本详情 {caseSummary.case_id}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

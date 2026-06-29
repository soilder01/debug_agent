import type { SpreadsheetWritebackAuditCounts } from "../api/client";
import { ActionRow, MetricStrip } from "../ui/ProductPrimitives";

type WritebackAuditSummaryProps = {
  summary: SpreadsheetWritebackAuditCounts;
  onLoadStatus: (status: string) => void;
};

export function WritebackAuditSummary({ summary, onLoadStatus }: WritebackAuditSummaryProps) {
  const succeededCount = summary.by_status.succeeded ?? 0;
  const failedCount = summary.by_status.failed ?? 0;
  const skippedCount = summary.by_status.skipped ?? 0;

  return (
    <>
      <MetricStrip
        label="回写审计健康指标"
        metrics={[
          { label: "总数", value: summary.total_count, helper: "全部写回审计" },
          { label: "成功", value: succeededCount, helper: "已完成写回" },
          { label: "失败", value: failedCount, helper: "可排查或重试" },
          { label: "跳过", value: skippedCount, helper: "未执行写回" }
        ]}
      />
      <p>审计总数：{summary.total_count}</p>
      <p>写回成功：{succeededCount}</p>
      <p>写回失败：{failedCount}</p>
      <p>写回跳过：{skippedCount}</p>
      <ActionRow label="审计筛选">
        <button type="button" onClick={() => onLoadStatus("succeeded")}>
          查看成功审计
        </button>
        <button type="button" onClick={() => onLoadStatus("failed")}>
          查看失败审计
        </button>
        <button type="button" onClick={() => onLoadStatus("skipped")}>
          查看跳过审计
        </button>
      </ActionRow>
    </>
  );
}

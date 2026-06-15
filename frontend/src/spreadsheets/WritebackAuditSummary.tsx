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
        label="Writeback audit health metrics"
        metrics={[
          { label: "Total", value: summary.total_count, helper: "All writeback audits" },
          { label: "Succeeded", value: succeededCount, helper: "Completed writes" },
          { label: "Failed", value: failedCount, helper: "Retry candidates" },
          { label: "Skipped", value: skippedCount, helper: "No-op outcomes" }
        ]}
      />
      <p>Writeback audit total：{summary.total_count}</p>
      <p>Writeback audit succeeded：{succeededCount}</p>
      <p>Writeback audit failed：{failedCount}</p>
      <p>Writeback audit skipped：{skippedCount}</p>
      <ActionRow label="Writeback audit filters">
        <button type="button" onClick={() => onLoadStatus("succeeded")}>
          View succeeded writeback audits
        </button>
        <button type="button" onClick={() => onLoadStatus("failed")}>
          View failed writeback audits
        </button>
        <button type="button" onClick={() => onLoadStatus("skipped")}>
          View skipped writeback audits
        </button>
      </ActionRow>
    </>
  );
}

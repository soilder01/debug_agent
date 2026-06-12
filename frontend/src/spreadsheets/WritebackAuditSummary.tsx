import type { SpreadsheetWritebackAuditCounts } from "../api/client";

type WritebackAuditSummaryProps = {
  summary: SpreadsheetWritebackAuditCounts;
  onLoadStatus: (status: string) => void;
};

export function WritebackAuditSummary({ summary, onLoadStatus }: WritebackAuditSummaryProps) {
  return (
    <>
      <p>Writeback audit total：{summary.total_count}</p>
      <p>Writeback audit succeeded：{summary.by_status.succeeded ?? 0}</p>
      <p>Writeback audit failed：{summary.by_status.failed ?? 0}</p>
      <p>Writeback audit skipped：{summary.by_status.skipped ?? 0}</p>
      <button type="button" onClick={() => onLoadStatus("succeeded")}>
        View succeeded writeback audits
      </button>
      <button type="button" onClick={() => onLoadStatus("failed")}>
        View failed writeback audits
      </button>
      <button type="button" onClick={() => onLoadStatus("skipped")}>
        View skipped writeback audits
      </button>
    </>
  );
}

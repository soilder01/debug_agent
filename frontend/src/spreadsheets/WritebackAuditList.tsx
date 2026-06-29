import type { SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { WritebackAuditRow } from "./WritebackAuditRow";

type WritebackAuditListProps = {
  audits: SpreadsheetWritebackAudit[];
  activeFilter: string | null;
  totalCount: number;
  writebackResult: SpreadsheetWritebackResult | null;
  onOpenJob: (jobId: string) => void;
  onRetry: (audit: SpreadsheetWritebackAudit) => void;
  onLoadMore: () => void;
};

export function WritebackAuditList({
  audits,
  activeFilter,
  totalCount,
  writebackResult,
  onOpenJob,
  onRetry,
  onLoadMore
}: WritebackAuditListProps) {
  return (
    <section className="writeback-audit-list" aria-label="回写审计列表">
      <p>审计记录总数：{totalCount}</p>
      <p>当前筛选：{filterLabel(activeFilter)}</p>
      <ul aria-label="飞书写回审计记录">
        {audits.map((audit) => (
          <WritebackAuditRow key={audit.job_id} audit={audit} onOpenJob={onOpenJob} onRetry={onRetry} />
        ))}
      </ul>
      {writebackResult ? (
        <>
          <p>最近重试写回行：{writebackResult.row_id}</p>
          <ul aria-label="写回字段">
            {Object.entries(writebackResult.fields).map(([key, value]) => (
              <li key={key}>
                {key}：{value}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {audits.length < totalCount ? (
        <button type="button" onClick={onLoadMore}>
          加载更多审计记录
        </button>
      ) : null}
    </section>
  );
}

function filterLabel(status: string | null): string {
  if (status === "succeeded") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  return "全部";
}

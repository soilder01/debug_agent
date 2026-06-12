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
    <>
      <p>Writeback audits total：{totalCount}</p>
      <p>Writeback audit filter：{activeFilter ?? "all"}</p>
      <ul aria-label="Spreadsheet writeback audits">
        {audits.map((audit) => (
          <WritebackAuditRow key={audit.job_id} audit={audit} onOpenJob={onOpenJob} onRetry={onRetry} />
        ))}
      </ul>
      {writebackResult ? (
        <>
          <p>Spreadsheet writeback row：{writebackResult.row_id}</p>
          <ul aria-label="Spreadsheet writeback fields">
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
          Load more writeback audits
        </button>
      ) : null}
    </>
  );
}

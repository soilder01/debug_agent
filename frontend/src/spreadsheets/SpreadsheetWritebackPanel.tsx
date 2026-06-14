import type { SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { NativeWritebackFields } from "./NativeWritebackFields";

type SpreadsheetWritebackPanelProps = {
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  onWriteReport: () => void;
  onLoadAudit: () => void;
};

export function SpreadsheetWritebackPanel({
  writebackResult,
  writebackAudit,
  onWriteReport,
  onLoadAudit
}: SpreadsheetWritebackPanelProps) {
  return (
    <section>
      <h2>Spreadsheet Writeback</h2>
      <button type="button" onClick={onWriteReport}>
        Write report to spreadsheet
      </button>
      <button type="button" onClick={onLoadAudit}>
        Load writeback audit
      </button>
      {writebackResult ? (
        <>
          <p>Spreadsheet writeback row：{writebackResult.row_id}</p>
          <NativeWritebackFields fields={writebackResult.fields} />
          <ul aria-label="Spreadsheet writeback fields">
            {Object.entries(writebackResult.fields).map(([key, value]) => (
              <li key={key}>
                {key}：{value}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {writebackAudit ? (
        <>
          <p>Writeback audit status：{writebackAudit.status}</p>
          <p>Writeback audit row：{writebackAudit.row_id}</p>
          <p>Writeback audit report URL：{writebackAudit.report_url}</p>
          <p>Writeback audit updated：{writebackAudit.updated_at}</p>
          {writebackAudit.error_message ? <p role="alert">Writeback audit error：{writebackAudit.error_message}</p> : null}
        </>
      ) : null}
    </section>
  );
}

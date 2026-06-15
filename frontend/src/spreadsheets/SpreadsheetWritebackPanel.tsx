import type { SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { ActionRow, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";
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
    <ProductSurface
      title="Spreadsheet Writeback"
      eyebrow="Writeback"
      description="Persist final debug conclusions and inspect the latest writeback audit."
      className="writeback-panel"
    >
      <ActionRow label="Spreadsheet writeback actions">
        <button type="button" onClick={onWriteReport}>
          Write report to spreadsheet
        </button>
        <button type="button" onClick={onLoadAudit}>
          Load writeback audit
        </button>
      </ActionRow>
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
          <StatusBadge tone={writebackTone(writebackAudit.status)}>{writebackAudit.status}</StatusBadge>
          <p>Writeback audit status：{writebackAudit.status}</p>
          <p>Writeback audit row：{writebackAudit.row_id}</p>
          <p>Writeback audit report URL：{writebackAudit.report_url}</p>
          <p>Writeback audit updated：{writebackAudit.updated_at}</p>
          {writebackAudit.error_message ? <p role="alert">Writeback audit error：{writebackAudit.error_message}</p> : null}
        </>
      ) : null}
    </ProductSurface>
  );
}

function writebackTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "skipped") {
    return "warning";
  }
  if (status === "succeeded") {
    return "success";
  }
  return "neutral";
}

type SpreadsheetControlsPanelProps = {
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  onSpreadsheetUrlChange: (value: string) => void;
  onSpreadsheetIdChange: (value: string) => void;
  onSheetIdChange: (value: string) => void;
  onUseSpreadsheetUrl: () => void;
  onCheckLarkStatus: () => void;
  onSyncSpreadsheet: () => void;
  onLoadWritebackAuditSummary: () => void;
  onLoadWritebackAudits: (status: string | null) => void;
};

export function SpreadsheetControlsPanel({
  spreadsheetUrl,
  spreadsheetId,
  sheetId,
  onSpreadsheetUrlChange,
  onSpreadsheetIdChange,
  onSheetIdChange,
  onUseSpreadsheetUrl,
  onCheckLarkStatus,
  onSyncSpreadsheet,
  onLoadWritebackAuditSummary,
  onLoadWritebackAudits
}: SpreadsheetControlsPanelProps) {
  return (
    <>
      <label htmlFor="lark-spreadsheet-url">Lark spreadsheet URL</label>
      <input
        id="lark-spreadsheet-url"
        value={spreadsheetUrl}
        onChange={(event) => onSpreadsheetUrlChange(event.target.value)}
      />
      <button type="button" onClick={onUseSpreadsheetUrl}>
        Use spreadsheet URL
      </button>
      <label htmlFor="spreadsheet-id">Spreadsheet ID</label>
      <input id="spreadsheet-id" value={spreadsheetId} onChange={(event) => onSpreadsheetIdChange(event.target.value)} />
      <label htmlFor="sheet-id">Sheet ID</label>
      <input id="sheet-id" value={sheetId} onChange={(event) => onSheetIdChange(event.target.value)} />
      <button type="button" onClick={onCheckLarkStatus}>
        Check Lark status
      </button>
      <button type="button" onClick={onSyncSpreadsheet}>
        Sync spreadsheet rows
      </button>
      <button type="button" onClick={onLoadWritebackAuditSummary}>
        Load writeback audit summary
      </button>
      <button type="button" onClick={() => onLoadWritebackAudits(null)}>
        Load all writeback audits
      </button>
      <button type="button" onClick={() => onLoadWritebackAudits("succeeded")}>
        Load succeeded writeback audits
      </button>
      <button type="button" onClick={() => onLoadWritebackAudits("failed")}>
        Load failed writeback audits
      </button>
      <button type="button" onClick={() => onLoadWritebackAudits("skipped")}>
        Load skipped writeback audits
      </button>
    </>
  );
}

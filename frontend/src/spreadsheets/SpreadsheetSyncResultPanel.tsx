import type { SpreadsheetSyncResponse } from "../api/client";

type SpreadsheetSyncResultPanelProps = {
  result: SpreadsheetSyncResponse;
};

export function SpreadsheetSyncResultPanel({ result }: SpreadsheetSyncResultPanelProps) {
  return (
    <>
      <p>Spreadsheet 同步样本：{result.imported_case_ids.length}</p>
      <p>
        Spreadsheet 同步行：
        {result.imported_rows.length === 0
          ? "无"
          : result.imported_rows.map((row) => `${row.sheet_row_id}:${row.case_id}`).join(", ")}
      </p>
      <p>
        Spreadsheet 同步拒绝：
        {result.rejected_rows.length === 0
          ? "无"
          : result.rejected_rows.map((row) => `${row.row_index}:${row.sheet_row_id}:${row.error_message}`).join(", ")}
      </p>
    </>
  );
}

import type { SpreadsheetRowImportResponse } from "../api/client";

type SpreadsheetImportResultPanelProps = {
  result: SpreadsheetRowImportResponse;
};

export function SpreadsheetImportResultPanel({ result }: SpreadsheetImportResultPanelProps) {
  return (
    <>
      <p>Spreadsheet 导入样本：{result.imported_case_ids.length}</p>
      <p>
        Spreadsheet 导入行：
        {result.imported_rows.length === 0
          ? "无"
          : result.imported_rows.map((row) => `${row.sheet_row_id}:${row.case_id}`).join(", ")}
      </p>
      <p>
        Spreadsheet 导入拒绝：
        {result.rejected_rows.length === 0
          ? "无"
          : result.rejected_rows.map((row) => `${row.row_index}:${row.sheet_row_id}:${row.error_message}`).join(", ")}
      </p>
    </>
  );
}

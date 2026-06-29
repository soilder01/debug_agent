import type { SpreadsheetRowImportResponse } from "../api/client";

type SpreadsheetImportResultPanelProps = {
  result: SpreadsheetRowImportResponse;
};

export function SpreadsheetImportResultPanel({ result }: SpreadsheetImportResultPanelProps) {
  return (
    <>
      <p>表格导入样本：{result.imported_case_ids.length}</p>
      <p>
        表格导入行：
        {result.imported_rows.length === 0
          ? "无"
          : result.imported_rows.map((row) => `${row.sheet_row_id}:${row.case_id}`).join(", ")}
      </p>
      <p>
        表格导入拒绝：
        {result.rejected_rows.length === 0
          ? "无"
          : result.rejected_rows.map((row) => `${row.row_index}:${row.sheet_row_id}:${row.error_message}`).join(", ")}
      </p>
      <p>批量创建：{result.jobs.length}</p>
      {result.jobs.map((job) => (
        <p key={job.job_id}>{job.job_id}：{job.status}</p>
      ))}
    </>
  );
}

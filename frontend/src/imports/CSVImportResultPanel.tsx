import type { CsvImportResponse } from "../api/client";

type CSVImportResultPanelProps = {
  result: CsvImportResponse;
};

export function CSVImportResultPanel({ result }: CSVImportResultPanelProps) {
  return (
    <>
      <p>CSV 导入样本：{result.imported_case_ids.length}</p>
      <p>
        CSV 导入拒绝：
        {result.rejected_rows.length === 0
          ? "无"
          : result.rejected_rows.map((row) => `${row.row_number}:${row.error_message}`).join(", ")}
      </p>
      <p>批量创建：{result.jobs.length}</p>
      {result.jobs.map((job) => (
        <p key={job.job_id}>{job.job_id}：{job.status}</p>
      ))}
    </>
  );
}

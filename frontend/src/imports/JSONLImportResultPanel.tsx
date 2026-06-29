import type { JsonlImportResponse } from "../api/client";

type JSONLImportResultPanelProps = {
  result: JsonlImportResponse;
};

export function JSONLImportResultPanel({ result }: JSONLImportResultPanelProps) {
  return (
    <>
      <p>导入样本：{result.imported_case_ids.length}</p>
      <p>
        导入拒绝：
        {result.rejected_lines.length === 0
          ? "无"
          : result.rejected_lines.map((line) => `${line.line_number}:${line.error_message}`).join(", ")}
      </p>
      <p>批量创建：{result.jobs.length}</p>
      {result.jobs.map((job) => (
        <p key={job.job_id}>{job.job_id}：{job.status}</p>
      ))}
    </>
  );
}

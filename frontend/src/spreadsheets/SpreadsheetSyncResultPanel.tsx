import type { SpreadsheetSyncResponse } from "../api/client";

type SpreadsheetSyncResultPanelProps = {
  result: SpreadsheetSyncResponse;
};

export function SpreadsheetSyncResultPanel({ result }: SpreadsheetSyncResultPanelProps) {
  const autoClosureReports = result.auto_closure_reports ?? [];
  return (
    <>
      <p>表格同步样本：{result.imported_case_ids.length}</p>
      <p>
        表格同步行：
        {result.imported_rows.length === 0
          ? "无"
          : result.imported_rows.map((row) => `${row.sheet_row_id}:${row.case_id}`).join(", ")}
      </p>
      <p>
        表格同步拒绝：
        {result.rejected_rows.length === 0
          ? "无"
          : result.rejected_rows.map((row) => `${row.row_index}:${row.sheet_row_id}:${row.error_message}`).join(", ")}
      </p>
      <p>表格同步任务：{result.jobs.length}</p>
      {result.jobs.map((job) => (
        <p key={job.job_id}>{job.job_id}：{job.status}</p>
      ))}
      {autoClosureReports.length > 0 ? (
        <section aria-label="表格自动闭环报告">
          <p>表格闭环报告：{autoClosureReports.length}</p>
          {autoClosureReports.map((report) => (
            <p key={report.job_id}>
              <a href={report.report_artifact_url}>{report.case_id} 自动闭环报告</a>
              <span> 写回状态：{statusLabel(report.writeback_status)}</span>
            </p>
          ))}
        </section>
      ) : null}
    </>
  );
}

function statusLabel(status: string): string {
  if (status === "succeeded") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  return status || "未知";
}

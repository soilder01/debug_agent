import type { WorkerStatus } from "../api/client";
import { MetricStrip, StatusBadge } from "../ui/ProductPrimitives";
import { displayEnabled } from "../ui/statusLabels";

type WorkerStatusPanelProps = {
  status: WorkerStatus;
};

export function WorkerStatusPanel({ status }: WorkerStatusPanelProps) {
  return (
    <>
      <StatusBadge tone={status.running ? "success" : "neutral"}>{status.running ? "运行中" : "已停止"}</StatusBadge>
      <MetricStrip
        label="后台进程运行指标"
        metrics={[
          { label: "已处理", value: status.processed_count, helper: "已完成队列任务" },
          { label: "错误", value: status.error_count, helper: "执行异常次数" },
          {
            label: "已恢复",
            value: status.recovered_stale_job_count ?? 0,
            helper: "卡住的运行中任务"
          },
          {
            label: "自动回写",
            value: displayEnabled(status.auto_writeback_enabled),
            helper: "飞书表格更新"
          }
        ]}
      />
      <p>进程运行中：{status.running ? "是" : "否"}</p>
      <p>已处理任务：{status.processed_count}</p>
      <p>进程错误：{status.error_count}</p>
      <p>已恢复卡住任务：{status.recovered_stale_job_count ?? 0}</p>
      <p>自动回写配置：{displayEnabled(status.auto_writeback_enabled)}</p>
      <p>完成回调：{displayEnabled(status.completion_hook_enabled)}</p>
      <p>报告基础 URL：{status.report_base_url}</p>
      {status.last_error ? <p role="alert">进程错误：{status.last_error}</p> : null}
    </>
  );
}

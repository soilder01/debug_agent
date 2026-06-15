import type { WorkerStatus } from "../api/client";
import { MetricStrip, StatusBadge } from "../ui/ProductPrimitives";

type WorkerStatusPanelProps = {
  status: WorkerStatus;
};

export function WorkerStatusPanel({ status }: WorkerStatusPanelProps) {
  return (
    <>
      <StatusBadge tone={status.running ? "success" : "neutral"}>{status.running ? "Running" : "Stopped"}</StatusBadge>
      <MetricStrip
        label="Worker runtime metrics"
        metrics={[
          { label: "Processed", value: status.processed_count, helper: "Completed queue items" },
          { label: "Errors", value: status.error_count, helper: "Worker execution failures" },
          {
            label: "Writeback",
            value: status.auto_writeback_enabled ? "On" : "Off",
            helper: "Automatic spreadsheet updates"
          }
        ]}
      />
      <p>Worker running：{String(status.running)}</p>
      <p>Worker processed：{status.processed_count}</p>
      <p>Worker errors：{status.error_count}</p>
      <p>Worker auto writeback setting：{status.auto_writeback_enabled ? "enabled" : "disabled"}</p>
      <p>Worker auto writeback：{status.completion_hook_enabled ? "enabled" : "disabled"}</p>
      <p>Worker report base URL：{status.report_base_url}</p>
      {status.last_error ? <p role="alert">Worker error：{status.last_error}</p> : null}
    </>
  );
}

import type { WorkerStatus } from "../api/client";

type WorkerStatusPanelProps = {
  status: WorkerStatus;
};

export function WorkerStatusPanel({ status }: WorkerStatusPanelProps) {
  return (
    <>
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

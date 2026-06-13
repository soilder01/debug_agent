import type { ObservabilitySummary } from "../api/client";

type ObservabilitySummaryPanelProps = {
  summary: ObservabilitySummary;
  onLoadFailedJobs?: () => void;
  onLoadFailedWritebacks?: () => void;
  onStartWorker?: () => void;
};

export function ObservabilitySummaryPanel({
  summary,
  onLoadFailedJobs,
  onLoadFailedWritebacks,
  onStartWorker
}: ObservabilitySummaryPanelProps) {
  return (
    <section>
      <h2>Observability</h2>
      <p>Observed jobs total：{summary.jobs.total_count}</p>
      <p>Observed jobs pending：{summary.jobs.pending_count}</p>
      <p>Observed jobs running：{summary.jobs.running_count}</p>
      <p>Observed jobs completed：{summary.jobs.completed_count}</p>
      <p>Observed jobs failed：{summary.jobs.failed_count}</p>
      <p>Observed worker running：{String(summary.worker.running)}</p>
      <p>Observed worker processed：{summary.worker.processed_count}</p>
      <p>Observed worker errors：{summary.worker.error_count}</p>
      <p>Observed worker auto writeback：{summary.worker.auto_writeback_enabled ? "enabled" : "disabled"}</p>
      <p>Observed worker completion hook：{summary.worker.completion_hook_enabled ? "enabled" : "disabled"}</p>
      {summary.worker.last_error ? <p role="alert">Observed worker last error：{summary.worker.last_error}</p> : null}
      <p>Observed writeback audits total：{summary.writeback_audits.total_count}</p>
      <p>Observed writeback succeeded：{summary.writeback_audits.by_status.succeeded ?? 0}</p>
      <p>Observed writeback failed：{summary.writeback_audits.by_status.failed ?? 0}</p>
      <p>Observed writeback skipped：{summary.writeback_audits.by_status.skipped ?? 0}</p>
      <p>Observed evidence total：{summary.evidence.total_evidence}</p>
      <p>Observed evidence failed judgements：{summary.evidence.failed_judgements}</p>
      <p>Observed evidence parse errors：{summary.evidence.response_parse_errors}</p>
      <p>Observed evidence model call errors：{summary.evidence.model_call_errors}</p>
      <p>Observed evidence avg latency：{summary.evidence.average_latency_ms}ms</p>
      <p>Observed health：{summary.health.level}</p>
      {summary.health.reasons.map((reason) => (
        <p key={reason}>Observed health reason：{reason}</p>
      ))}
      {summary.health.actions.map((action) => (
        <p key={action}>Recommended action：{action}</p>
      ))}
      {onLoadFailedJobs ? (
        <button type="button" onClick={onLoadFailedJobs}>
          Open failed jobs from observability
        </button>
      ) : null}
      {onLoadFailedWritebacks ? (
        <button type="button" onClick={onLoadFailedWritebacks}>
          Open failed writebacks from observability
        </button>
      ) : null}
      {onStartWorker ? (
        <button type="button" onClick={onStartWorker}>
          Start worker from observability
        </button>
      ) : null}
    </section>
  );
}

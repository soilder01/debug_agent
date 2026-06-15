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
  const strategyFeedback = summary.strategy_feedback ?? {
    total_follow_ups: 0,
    pending_count: 0,
    passed_stop_condition_count: 0,
    needs_escalation_count: 0
  };
  const targetedProbeFeedback = summary.targeted_probe_feedback ?? {
    total_probes: 0,
    pending_count: 0,
    target_cleared_count: 0,
    target_still_failing_count: 0,
    inconclusive_count: 0,
    max_depth_reached_count: 0
  };
  const humanHandoffFeedback = summary.human_handoff_feedback ?? {
    total_handoffs: 0,
    pending_count: 0,
    acknowledged_count: 0,
    in_progress_count: 0,
    resolved_count: 0,
    wont_fix_count: 0,
    open_count: 0
  };
  const finalAttributionVerificationFeedback = summary.final_attribution_verification_feedback ?? {
    total_verifications: 0,
    pending_count: 0,
    resolved_count: 0,
    not_resolved_count: 0,
    inconclusive_count: 0
  };
  const finalAttributionRecoveryFeedback = summary.final_attribution_recovery_feedback ?? {
    total_recoveries: 0,
    pending_count: 0,
    closed_count: 0,
    reopen_count: 0,
    inconclusive_count: 0
  };
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
      <p>Observed model calls：{summary.usage.model_call_count}</p>
      <p>Observed prompt chars：{summary.usage.prompt_character_count}</p>
      <p>Observed estimated cost units：{summary.usage.estimated_cost_units}</p>
      <p>Observed usage budget：{summary.usage.budget_units}</p>
      <p>Observed budget status：{summary.usage.budget_status}</p>
      <p>Observed budget utilization：{summary.usage.budget_utilization}</p>
      <p>Observed budget enforcement：{summary.usage.budget_enforcement_enabled ? "enabled" : "disabled"}</p>
      <p>Observed strategy follow-ups：{strategyFeedback.total_follow_ups}</p>
      <p>Observed strategy pending：{strategyFeedback.pending_count}</p>
      <p>Observed strategy passed stop condition：{strategyFeedback.passed_stop_condition_count}</p>
      <p>Observed strategy needs escalation：{strategyFeedback.needs_escalation_count}</p>
      <p>Observed targeted probes：{targetedProbeFeedback.total_probes}</p>
      <p>Observed targeted pending：{targetedProbeFeedback.pending_count}</p>
      <p>Observed targeted cleared：{targetedProbeFeedback.target_cleared_count}</p>
      <p>Observed targeted still failing：{targetedProbeFeedback.target_still_failing_count}</p>
      <p>Observed targeted inconclusive：{targetedProbeFeedback.inconclusive_count}</p>
      <p>Observed targeted max depth reached：{targetedProbeFeedback.max_depth_reached_count}</p>
      <p>Observed human handoffs：{humanHandoffFeedback.total_handoffs}</p>
      <p>Observed handoff pending：{humanHandoffFeedback.pending_count}</p>
      <p>Observed handoff acknowledged：{humanHandoffFeedback.acknowledged_count}</p>
      <p>Observed handoff in progress：{humanHandoffFeedback.in_progress_count}</p>
      <p>Observed handoff resolved：{humanHandoffFeedback.resolved_count}</p>
      <p>Observed handoff wont fix：{humanHandoffFeedback.wont_fix_count}</p>
      <p>Observed handoff open：{humanHandoffFeedback.open_count}</p>
      <p>Observed final attribution verifications：{finalAttributionVerificationFeedback.total_verifications}</p>
      <p>Observed final attribution pending：{finalAttributionVerificationFeedback.pending_count}</p>
      <p>Observed final attribution resolved：{finalAttributionVerificationFeedback.resolved_count}</p>
      <p>Observed final attribution not resolved：{finalAttributionVerificationFeedback.not_resolved_count}</p>
      <p>Observed final attribution inconclusive：{finalAttributionVerificationFeedback.inconclusive_count}</p>
      <p>Observed final attribution recoveries：{finalAttributionRecoveryFeedback.total_recoveries}</p>
      <p>Observed final attribution recovery pending：{finalAttributionRecoveryFeedback.pending_count}</p>
      <p>Observed final attribution recovery closed：{finalAttributionRecoveryFeedback.closed_count}</p>
      <p>Observed final attribution recovery reopen：{finalAttributionRecoveryFeedback.reopen_count}</p>
      <p>Observed final attribution recovery inconclusive：{finalAttributionRecoveryFeedback.inconclusive_count}</p>
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

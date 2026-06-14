import type { DebugReport } from "../api/client";

type ReportPanelProps = {
  report: DebugReport;
  onSelectEvidence?: (evidenceId: string) => void;
};

export function ReportPanel({ report, onSelectEvidence }: ReportPanelProps) {
  const experimentSummary = report.experiment_summary;
  const artifactIds = experimentSummary?.artifact_ids?.length
    ? experimentSummary.artifact_ids
    : (experimentSummary?.image_artifact_ids ?? []);
  const failedTrialCount = experimentSummary?.failed_trial_count ?? 0;
  const evidenceCitations = report.evidence_citations ?? [];
  const stepSummaries = experimentSummary?.step_summaries ?? [];
  const ablationConclusion = report.suggested_sheet_fields["Ablation结论"];
  const rootCauseTrace = report.root_cause_trace ?? [];

  return (
    <section>
      <h2>Root Cause</h2>
      <p>类型：{report.root_cause.label}</p>
      <p>置信度：{report.root_cause.confidence}</p>
      <p>{report.root_cause.evidence_summary}</p>
      {experimentSummary ? (
        <>
          <h3>Replay Stability</h3>
          <p>复测稳定性：{experimentSummary.stability_label ?? "unknown"}</p>
          <p>复测通过率：{formatPercent(experimentSummary.success_rate ?? 0)}</p>
          <p>
            失败次数：{failedTrialCount}/{experimentSummary.total_trials}
          </p>
        </>
      ) : null}
      {stepSummaries.length > 0 ? (
        <>
          <h3>Experiment Trajectory</h3>
          <ul aria-label="Experiment step trajectory">
            {stepSummaries.map((step) => (
              <li key={step.step_name}>
                <p>步骤：{step.step_name}</p>
                <p>步骤通过率：{formatPercent(step.success_rate)}</p>
                <p>
                  步骤失败次数：{step.failed_trial_count}/{step.total_trials}
                </p>
                <p>Delta 类型：{step.delta_reasons.length > 0 ? step.delta_reasons.join(", ") : "无"}</p>
                <p>目标：{step.target_ids.length > 0 ? step.target_ids.join(", ") : "无"}</p>
                {step.ablation_variants?.length ? <p>Ablation：{step.ablation_variants.join(", ")}</p> : null}
                {step.ablation_modalities?.length ? <p>Ablation 模态：{step.ablation_modalities.join(", ")}</p> : null}
                <p>证据：{step.evidence_ids.join(", ")}</p>
                {onSelectEvidence && step.evidence_ids.length > 0 ? (
                  <ul aria-label={`${step.step_name} trajectory evidence`}>
                    {step.evidence_ids.map((evidenceId) => (
                      <li key={evidenceId}>
                        <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
                          {evidenceId}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p>产物：{step.artifact_ids.length > 0 ? step.artifact_ids.join(", ") : "无"}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {ablationConclusion ? (
        <section aria-label="Ablation diagnosis">
          <h3>Ablation Diagnosis</h3>
          <p>{ablationConclusion}</p>
        </section>
      ) : null}
      {rootCauseTrace.length > 0 ? (
        <>
          <h3>Root Cause Trace</h3>
          <ul aria-label="Root cause trace">
            {rootCauseTrace.map((trace) => (
              <li key={`${trace.evidence_id}:${trace.variant}`}>
                <p>步骤：{trace.step_name}</p>
                <p>变体：{trace.variant}</p>
                <p>模态：{trace.modalities.length > 0 ? trace.modalities.join(", ") : "无"}</p>
                <p>证据：{trace.evidence_id}</p>
                <p>Judge Score：{trace.judge_score}</p>
                <p>Delta：{trace.delta_reasons.length > 0 ? trace.delta_reasons.join(", ") : "无"}</p>
                <p>目标：{trace.target_ids.length > 0 ? trace.target_ids.join(", ") : "无"}</p>
                <p>产物：{trace.artifact_ids.length > 0 ? trace.artifact_ids.join(", ") : "无"}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>Evidence Artifacts</h3>
      <p>证据产物：{artifactIds.length}</p>
      {artifactIds.length > 0 ? (
        <ul>
          {artifactIds.map((artifactId) => (
            <li key={artifactId}>{artifactId}</li>
          ))}
        </ul>
      ) : null}
      {evidenceCitations.length > 0 ? (
        <>
          <h3>Evidence Citations</h3>
          <ul>
            {evidenceCitations.map((citation) => (
              <li key={`${citation.evidence_id}:${citation.box_id ?? "global"}:${citation.reason}`}>
                <p>引用证据：{citation.evidence_id}</p>
                <p>引用步骤：{citation.step_name}</p>
                <p>引用目标/区域：{citation.box_id ?? "global"}</p>
                <p>引用原因：{citation.reason}</p>
                {citation.artifact_ids.length > 0 ? <p>引用证据产物：{citation.artifact_ids.join(", ")}</p> : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>建议回填</h3>
      <dl>
        {Object.entries(report.suggested_sheet_fields).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

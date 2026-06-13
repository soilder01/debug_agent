import type { DebugReport } from "../api/client";

type ReportPanelProps = {
  report: DebugReport;
};

export function ReportPanel({ report }: ReportPanelProps) {
  const experimentSummary = report.experiment_summary;
  const artifactIds = experimentSummary?.artifact_ids?.length
    ? experimentSummary.artifact_ids
    : (experimentSummary?.image_artifact_ids ?? []);
  const failedTrialCount = experimentSummary?.failed_trial_count ?? 0;
  const evidenceCitations = report.evidence_citations ?? [];

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

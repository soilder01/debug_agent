import type { DebugReport } from "../api/client";

type ReportPanelProps = {
  report: DebugReport;
};

export function ReportPanel({ report }: ReportPanelProps) {
  const imageArtifactIds = report.experiment_summary?.image_artifact_ids ?? [];

  return (
    <section>
      <h2>Root Cause</h2>
      <p>类型：{report.root_cause.label}</p>
      <p>置信度：{report.root_cause.confidence}</p>
      <p>{report.root_cause.evidence_summary}</p>
      <h3>Visual Evidence</h3>
      <p>可视证据：{imageArtifactIds.length}</p>
      {imageArtifactIds.length > 0 ? (
        <ul>
          {imageArtifactIds.map((artifactId) => (
            <li key={artifactId}>{artifactId}</li>
          ))}
        </ul>
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

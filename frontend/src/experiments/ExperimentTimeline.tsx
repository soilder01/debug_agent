type ExperimentTimelineProps = {
  experiments: string[];
  summary: {
    total_trials: number;
    success_count: number;
    evidence_ids: string[];
  } | null;
  onSelectEvidence: (evidenceId: string) => void;
};

export function ExperimentTimeline({
  experiments,
  summary,
  onSelectEvidence
}: ExperimentTimelineProps) {
  return (
    <section>
      <h2>Experiment Plan</h2>
      {summary ? (
        <p>
          成功次数：{summary.success_count} / {summary.total_trials}，证据数：
          {summary.evidence_ids.length}
        </p>
      ) : null}
      {summary ? (
        <>
          <h3>Evidence</h3>
          <ul>
            {summary.evidence_ids.map((evidenceId) => (
              <li key={evidenceId}>
                <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
                  {evidenceId}
                </button>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <ol>
        {experiments.map((experiment) => (
          <li key={experiment}>{experiment}</li>
        ))}
      </ol>
    </section>
  );
}

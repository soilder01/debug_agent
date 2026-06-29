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
    <section className="experiment-timeline" aria-label="实验计划">
      <h2>实验计划</h2>
      {summary ? (
        <p>
          成功次数：{summary.success_count} / {summary.total_trials}，证据数：
          {summary.evidence_ids.length}
        </p>
      ) : null}
      {summary ? (
        <>
          <h3>证据</h3>
          <ul className="experiment-timeline__evidence" aria-label="实验证据">
            {summary.evidence_ids.map((evidenceId) => (
              <li className="experiment-timeline__row" key={evidenceId} data-anime-flow>
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
          <li className="experiment-timeline__row" key={experiment} data-anime-flow>
            {experiment}
          </li>
        ))}
      </ol>
    </section>
  );
}

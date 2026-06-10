type ExperimentTimelineProps = {
  experiments: string[];
  summary: {
    total_trials: number;
    success_count: number;
    evidence_ids: string[];
  } | null;
};

export function ExperimentTimeline({ experiments, summary }: ExperimentTimelineProps) {
  return (
    <section>
      <h2>Experiment Plan</h2>
      {summary ? (
        <p>
          成功次数：{summary.success_count} / {summary.total_trials}，证据数：
          {summary.evidence_ids.length}
        </p>
      ) : null}
      <ol>
        {experiments.map((experiment) => (
          <li key={experiment}>{experiment}</li>
        ))}
      </ol>
    </section>
  );
}

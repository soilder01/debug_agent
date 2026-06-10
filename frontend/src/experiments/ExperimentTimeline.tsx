type ExperimentTimelineProps = {
  experiments: string[];
};

export function ExperimentTimeline({ experiments }: ExperimentTimelineProps) {
  return (
    <section>
      <h2>Experiment Plan</h2>
      <ol>
        {experiments.map((experiment) => (
          <li key={experiment}>{experiment}</li>
        ))}
      </ol>
    </section>
  );
}
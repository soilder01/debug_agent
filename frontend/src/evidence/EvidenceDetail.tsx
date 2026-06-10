import type { ExperimentEvidence } from "../api/client";

type EvidenceDetailProps = {
  evidence: ExperimentEvidence | null;
};

export function EvidenceDetail({ evidence }: EvidenceDetailProps) {
  if (!evidence) {
    return null;
  }

  return (
    <section>
      <h2>Evidence Detail</h2>
      <p>证据 ID：{evidence.evidence_id}</p>
      <p>实验步骤：{evidence.step_name}</p>
      <p>Trial：{evidence.trial}</p>
      <p>Judge Score：{evidence.judge.score}</p>
      <h3>Judge Reasons</h3>
      <ul>
        {evidence.judge.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <h3>Raw Output</h3>
      <pre>{evidence.raw_output}</pre>
    </section>
  );
}

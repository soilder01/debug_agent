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
      <p>模型名称：{evidence.model_name}</p>
      <p>模型 Provider：{evidence.model_provider}</p>
      <p>模型 ID：{evidence.model_id}</p>
      <p>调用耗时：{evidence.latency_ms}ms</p>
      <p>Prompt 长度：{evidence.request_summary.prompt_length ?? 0}</p>
      <p>包含图片：{String(evidence.request_summary.has_image ?? false)}</p>
      <p>图片 URI Scheme：{evidence.request_summary.image_uri_scheme || "无"}</p>
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

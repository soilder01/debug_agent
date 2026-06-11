import type { ExperimentEvidence } from "../api/client";

type EvidenceDetailProps = {
  evidence: ExperimentEvidence | null;
};

export function EvidenceDetail({ evidence }: EvidenceDetailProps) {
  if (!evidence) {
    return null;
  }
  const imageArtifacts = evidence.image_artifacts ?? [];

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
      {evidence.response_parse_error ? <p>解析错误：{evidence.response_parse_error}</p> : null}
      {evidence.model_call_error_type ? <p>模型调用错误类型：{evidence.model_call_error_type}</p> : null}
      {evidence.model_call_error_message ? <p>模型调用错误信息：{evidence.model_call_error_message}</p> : null}
      {imageArtifacts.length > 0 ? (
        <>
          <h3>Image Artifacts</h3>
          <ul>
            {imageArtifacts.map((artifact) => (
              <li key={artifact.artifact_id}>
                <h4>Artifact {artifact.artifact_id}</h4>
                <p>类型：{artifact.kind}</p>
                <p>源图片：{artifact.source_image_uri}</p>
                <p>派生图片：{artifact.derived_image_uri || "无"}</p>
                {artifact.region ? (
                  <p>
                    区域：x={artifact.region.x}, y={artifact.region.y}, width={artifact.region.width}, height=
                    {artifact.region.height}, unit={artifact.region.unit}, label={artifact.region.label || "无"}
                  </p>
                ) : (
                  <p>区域：无</p>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : null}
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

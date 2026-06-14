import type { ExperimentEvidence } from "../api/client";

type EvidenceDetailProps = {
  evidence: ExperimentEvidence | null;
};

export function EvidenceDetail({ evidence }: EvidenceDetailProps) {
  if (!evidence) {
    return null;
  }
  const imageArtifacts = evidence.image_artifacts ?? [];
  const genericArtifacts = evidence.artifacts ?? [];
  const judgeDeltas = evidence.judge.deltas ?? [];

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
      {genericArtifacts.length > 0 ? (
        <>
          <h3>Evidence Artifacts</h3>
          <ul>
            {genericArtifacts.map((artifact) => (
              <li key={artifact.artifact_id}>
                <h4>Artifact {artifact.artifact_id}</h4>
                <p>类型：{artifact.kind}</p>
                <p>媒介：{artifact.artifact_type}</p>
                <p>源 URI：{artifact.source_uri || "无"}</p>
                <p>派生 URI：{artifact.derived_uri || "无"}</p>
                <p>元数据：{JSON.stringify(artifact.metadata)}</p>
                <ArtifactNativeContext metadata={artifact.metadata} />
                {artifact.preview_url ? (
                  <>
                    <p>
                      <a href={artifact.preview_url} target="_blank" rel="noreferrer">
                        打开证据预览 {artifact.artifact_id}
                      </a>
                    </p>
                    <img alt={`Artifact preview ${artifact.artifact_id}`} src={artifact.preview_url} />
                  </>
                ) : (
                  <p>预览：无</p>
                )}
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
      ) : imageArtifacts.length > 0 ? (
        <>
          <h3>Evidence Artifacts</h3>
          <ul>
            {imageArtifacts.map((artifact) => (
              <li key={artifact.artifact_id}>
                <h4>Artifact {artifact.artifact_id}</h4>
                <p>类型：{artifact.kind}</p>
                <p>源图片：{artifact.source_image_uri}</p>
                <p>派生图片：{artifact.derived_image_uri || "无"}</p>
                {artifact.preview_image_url ? (
                  <>
                    <p>
                      <a href={artifact.preview_image_url} target="_blank" rel="noreferrer">
                        打开裁剪图 {artifact.artifact_id}
                      </a>
                    </p>
                    <img alt={`Crop preview ${artifact.artifact_id}`} src={artifact.preview_image_url} />
                  </>
                ) : (
                  <p>预览图：无</p>
                )}
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
      {judgeDeltas.length > 0 ? (
        <>
          <h3>Judge Deltas</h3>
          <ul aria-label="Judge deltas">
            {judgeDeltas.map((delta) => (
              <li key={`${delta.target_id}:${delta.reason}`}>
                <p>目标：{delta.target_id}</p>
                <p>原因：{delta.reason}</p>
                <p>期望：{delta.expected ?? "无"}</p>
                <p>实际：{delta.actual ?? "无"}</p>
                <p>元数据：{JSON.stringify(delta.metadata)}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>Raw Output</h3>
      <pre>{evidence.raw_output}</pre>
    </section>
  );
}

type ArtifactNativeContextProps = {
  metadata: Record<string, unknown>;
};

function ArtifactNativeContext({ metadata }: ArtifactNativeContextProps) {
  const targetId = stringValue(metadata.target_id);
  const expectedRegion = regionValue(metadata.expected_region);
  const actualRegion = regionValue(metadata.actual_region);
  const expectedSegment = segmentValue(metadata.expected_segment);
  const actualSegment = segmentValue(metadata.actual_segment);
  const expectedModalities = stringArrayValue(metadata.expected_modalities);
  const actualModalities = stringArrayValue(metadata.actual_modalities);
  const expectedConflictType = stringValue(metadata.expected_conflict_type);
  const actualConflictType = stringValue(metadata.actual_conflict_type);
  const hasContext =
    targetId ||
    expectedRegion ||
    actualRegion ||
    expectedSegment ||
    actualSegment ||
    expectedModalities.length > 0 ||
    actualModalities.length > 0 ||
    expectedConflictType ||
    actualConflictType;

  if (!hasContext) {
    return null;
  }

  return (
    <section aria-label="Artifact native context">
      {targetId ? <p>目标：{targetId}</p> : null}
      {expectedRegion ? <p>期望区域：{formatRegion(expectedRegion)}</p> : null}
      {actualRegion ? <p>实际区域：{formatRegion(actualRegion)}</p> : null}
      {expectedSegment ? <p>期望片段：{formatSegment(expectedSegment)}</p> : null}
      {actualSegment ? <p>实际片段：{formatSegment(actualSegment)}</p> : null}
      {expectedModalities.length > 0 ? <p>期望模态：{expectedModalities.join(", ")}</p> : null}
      {actualModalities.length > 0 ? <p>实际模态：{actualModalities.join(", ")}</p> : null}
      {expectedConflictType || actualConflictType ? (
        <p>冲突类型：{expectedConflictType || "无"} → {actualConflictType || "无"}</p>
      ) : null}
    </section>
  );
}

type RegionMetadata = {
  x: number;
  y: number;
  width: number;
  height: number;
  unit: string;
  label: string;
};

type SegmentMetadata = {
  start_ms: number;
  end_ms: number;
  label: string;
};

function regionValue(value: unknown): RegionMetadata | null {
  if (!isRecord(value)) {
    return null;
  }
  const x = numberValue(value.x);
  const y = numberValue(value.y);
  const width = numberValue(value.width);
  const height = numberValue(value.height);
  if (x === null || y === null || width === null || height === null) {
    return null;
  }
  return {
    x,
    y,
    width,
    height,
    unit: stringValue(value.unit) || "pixel",
    label: stringValue(value.label) || "无"
  };
}

function segmentValue(value: unknown): SegmentMetadata | null {
  if (!isRecord(value)) {
    return null;
  }
  const startMs = numberValue(value.start_ms);
  const endMs = numberValue(value.end_ms);
  if (startMs === null || endMs === null) {
    return null;
  }
  return {
    start_ms: startMs,
    end_ms: endMs,
    label: stringValue(value.label) || "无"
  };
}

function formatRegion(region: RegionMetadata): string {
  return `x=${region.x}, y=${region.y}, width=${region.width}, height=${region.height}, unit=${region.unit}, label=${region.label}`;
}

function formatSegment(segment: SegmentMetadata): string {
  return `start=${segment.start_ms}ms, end=${segment.end_ms}ms, label=${segment.label}`;
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

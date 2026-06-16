import type { ExperimentEvidence } from "../api/client";
import { EmptyState, MetricStrip, ProductSurface } from "../ui/ProductPrimitives";

type EvidenceDetailProps = {
  evidence: ExperimentEvidence | null;
};

export function EvidenceDetail({ evidence }: EvidenceDetailProps) {
  if (!evidence) {
    return (
      <ProductSurface
        title="Evidence Detail"
        eyebrow="Evidence"
        description="Select an evidence record to inspect request metadata, artifacts, judge output, and raw model response."
        className="evidence-detail"
      >
        <EmptyState title="No evidence selected" description="Open evidence from a job, report trajectory, or artifact link." />
      </ProductSurface>
    );
  }
  const imageArtifacts = evidence.image_artifacts ?? [];
  const genericArtifacts = evidence.artifacts ?? [];
  const judgeDeltas = evidence.judge.deltas ?? [];
  const ablationVariant = stringValue(evidence.request_summary.ablation_variant);
  const ablationModalities = stringArrayValue(evidence.request_summary.ablation_modalities);

  return (
    <ProductSurface
      title="Evidence Detail"
      eyebrow="Evidence"
      description="Inspect the selected model call, request context, artifacts, judge result, and raw response."
      className="evidence-detail"
    >
      <section className="evidence-section" aria-label="Evidence request metadata">
        <MetricStrip
          label="Evidence summary metrics"
          metrics={[
            { label: "Trial", value: evidence.trial, helper: evidence.step_name },
            { label: "Latency", value: `${evidence.latency_ms}ms`, helper: evidence.model_name },
            { label: "Prompt", value: evidence.request_summary.prompt_length ?? 0, helper: "Characters" },
            { label: "Judge", value: evidence.judge.score, helper: "Score" }
          ]}
        />
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
        {ablationVariant ? <p>Ablation Variant：{ablationVariant}</p> : null}
        {ablationModalities.length > 0 ? <p>Ablation 模态：{ablationModalities.join(", ")}</p> : null}
        {evidence.response_parse_error ? <p>解析错误：{evidence.response_parse_error}</p> : null}
        {evidence.model_call_error_type ? <p>模型调用错误类型：{evidence.model_call_error_type}</p> : null}
        {evidence.model_call_error_message ? <p>模型调用错误信息：{evidence.model_call_error_message}</p> : null}
      </section>
      <section className="evidence-artifacts" aria-label="Evidence artifacts">
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
                <VideoSegmentAudit artifact={artifact} />
                <MultimodalConflictAudit artifact={artifact} />
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
        ) : (
          <EmptyState title="No evidence artifacts" description="This evidence record does not include media or manifest artifacts." />
        )}
      </section>
      <section className="evidence-section" aria-label="Judge result">
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
      </section>
      <section className="evidence-section" aria-label="Model raw output">
        <h3>Raw Output</h3>
        <pre>{evidence.raw_output}</pre>
      </section>
    </ProductSurface>
  );
}

type ArtifactNativeContextProps = {
  metadata: Record<string, unknown>;
};

type VideoSegmentAuditProps = {
  artifact: {
    artifact_id: string;
    kind: string;
    derived_uri: string;
    metadata: Record<string, unknown>;
  };
};

function VideoSegmentAudit({ artifact }: VideoSegmentAuditProps) {
  if (artifact.kind !== "video_segment_delta" || !artifact.derived_uri) {
    return null;
  }
  const expectedSegment = segmentValue(artifact.metadata.expected_segment);
  const actualSegment = segmentValue(artifact.metadata.actual_segment);
  const auditSegment = actualSegment ?? expectedSegment;
  const manifestType = stringValue(artifact.metadata.manifest_type) || "video_segment_delta";
  const manifestUrl = manifestArtifactUrl(artifact.derived_uri);
  const keyframeThumbnails = keyframeThumbnailValues(artifact.metadata.keyframe_thumbnails);

  return (
    <section aria-label="Video segment audit">
      <h5>Video Segment Audit</h5>
      <p>Manifest 类型：{manifestType}</p>
      {auditSegment ? <p>审计片段：{auditSegment.start_ms}ms → {auditSegment.end_ms}ms</p> : null}
      <p>审计标签：{expectedSegment?.label ?? "无"} → {actualSegment?.label ?? "无"}</p>
      <p>
        <a href={manifestUrl} target="_blank" rel="noreferrer">
          打开视频片段 manifest {artifact.artifact_id}
        </a>
      </p>
      {keyframeThumbnails.length > 0 ? (
        <section aria-label="Keyframe thumbnails">
          <h6>Keyframe Thumbnails</h6>
          <ul>
            {keyframeThumbnails.map((thumbnail) => (
              <li key={`${artifact.artifact_id}:${thumbnail.timestamp_ms}`}>
                <p>关键帧：{thumbnail.timestamp_ms}ms</p>
                <a href={thumbnail.preview_url} target="_blank" rel="noreferrer">
                  打开关键帧 thumbnail {artifact.artifact_id} {thumbnail.timestamp_ms}ms
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

function MultimodalConflictAudit({ artifact }: VideoSegmentAuditProps) {
  if (artifact.kind !== "multimodal_conflict_delta" || !artifact.derived_uri) {
    return null;
  }
  const manifestType = stringValue(artifact.metadata.manifest_type) || "multimodal_conflict_delta";
  const targetId = stringValue(artifact.metadata.target_id);
  const expectedModalities = stringArrayValue(artifact.metadata.expected_modalities);
  const actualModalities = stringArrayValue(artifact.metadata.actual_modalities);
  const expected = stringValue(artifact.metadata.expected) || "无";
  const actual = stringValue(artifact.metadata.actual) || "无";
  const manifestUrl = manifestArtifactUrl(artifact.derived_uri);

  return (
    <section aria-label="Multimodal conflict audit">
      <h5>Multimodal Conflict Audit</h5>
      <p>Manifest 类型：{manifestType}</p>
      {targetId ? <p>审计目标：{targetId}</p> : null}
      <p>审计模态：{formatList(expectedModalities)} → {formatList(actualModalities)}</p>
      <p>审计结论：{expected} → {actual}</p>
      <p>
        <a href={manifestUrl} target="_blank" rel="noreferrer">
          打开跨模态冲突 manifest {artifact.artifact_id}
        </a>
      </p>
    </section>
  );
}

function ArtifactNativeContext({ metadata }: ArtifactNativeContextProps) {
  const targetId = stringValue(metadata.target_id);
  const expectedRegion = regionValue(metadata.expected_region);
  const actualRegion = regionValue(metadata.actual_region);
  const expectedSegment = segmentValue(metadata.expected_segment);
  const actualSegment = segmentValue(metadata.actual_segment);
  const timestampDelta = timestampDeltaValue(metadata);
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
    timestampDelta ||
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
      {timestampDelta ? (
        <section aria-label="Video timestamp delta">
          <p>时间窗字段：{timestampDelta.field}</p>
          <p>期望时间窗：{timestampDelta.expectedRange}s</p>
          <p>实际时间：{timestampDelta.actualValue}s</p>
          <p>偏差：{timestampDelta.deltaSeconds}s</p>
        </section>
      ) : null}
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

type KeyframeThumbnailMetadata = {
  timestamp_ms: number;
  preview_url: string;
};

type TimestampDeltaMetadata = {
  field: string;
  expectedRange: string;
  actualValue: string;
  deltaSeconds: string;
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

function timestampDeltaValue(metadata: Record<string, unknown>): TimestampDeltaMetadata | null {
  const field = stringValue(metadata.field);
  if (field !== "start_s" && field !== "end_s") {
    return null;
  }
  const expectedRange =
    field === "start_s" ? stringValue(metadata.expected_start_s_range) : stringValue(metadata.expected_end_s_range);
  const actual = field === "start_s" ? numberValue(metadata.actual_start_s) : numberValue(metadata.actual_end_s);
  const deltaSeconds = numberValue(metadata.delta_seconds);
  if (!expectedRange || actual === null || deltaSeconds === null) {
    return null;
  }
  return {
    field,
    expectedRange,
    actualValue: formatSeconds(actual),
    deltaSeconds: formatSeconds(deltaSeconds)
  };
}

function keyframeThumbnailValues(value: unknown): KeyframeThumbnailMetadata[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }
    const timestampMs = numberValue(item.timestamp_ms);
    const previewUrl = stringValue(item.preview_url);
    if (timestampMs === null || !previewUrl) {
      return [];
    }
    return [{ timestamp_ms: timestampMs, preview_url: previewUrl }];
  });
}

function formatRegion(region: RegionMetadata): string {
  return `x=${region.x}, y=${region.y}, width=${region.width}, height=${region.height}, unit=${region.unit}, label=${region.label}`;
}

function formatSegment(segment: SegmentMetadata): string {
  return `start=${segment.start_ms}ms, end=${segment.end_ms}ms, label=${segment.label}`;
}

function formatSeconds(value: number): string {
  return Number.isInteger(value) ? value.toFixed(1) : String(value);
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(", ") : "无";
}

function manifestArtifactUrl(uri: string): string {
  if (uri.startsWith("/api/artifacts/manifests/")) {
    return uri;
  }
  if (uri.startsWith("file://")) {
    const pathParts = uri.split(/[\\/]/);
    const filename = decodeURIComponent(pathParts[pathParts.length - 1] ?? "");
    return filename ? `/api/artifacts/manifests/${filename}` : uri;
  }
  return uri;
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

import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ExperimentEvidence } from "../api/client";
import { EvidenceDetail } from "./EvidenceDetail";

afterEach(() => {
  cleanup();
});

describe("EvidenceDetail", () => {
  it("renders generic evidence artifacts before legacy image artifacts", () => {
    const evidence = {
      evidence_id: "case-1:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 42,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 25,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [
        {
          artifact_id: "case-1:baseline_replay:0:input-snapshot",
          kind: "input_snapshot",
          artifact_type: "request",
          source_uri: "file:///tmp/case-1.png",
          derived_uri: "",
          preview_url: "",
          region: null,
          metadata: {
            task_type: "classification",
            prompt_length: 42
          }
        },
        {
          artifact_id: "case-1:baseline_replay:0:structured-output",
          kind: "structured_output",
          artifact_type: "model_output",
          source_uri: "",
          derived_uri: "",
          preview_url: "",
          region: null,
          metadata: {
            raw_output_length: 128
          }
        }
      ],
      image_artifacts: [],
      raw_output: "{\"label\":\"negative\"}",
      judge: {
        score: 0,
        reasons: ["label mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Evidence Artifacts")).toBeInTheDocument();
    expect(screen.getByText("Artifact case-1:baseline_replay:0:input-snapshot")).toBeInTheDocument();
    expect(screen.getByText("类型：input_snapshot")).toBeInTheDocument();
    expect(screen.getByText("媒介：request")).toBeInTheDocument();
    expect(screen.getByText("源 URI：file:///tmp/case-1.png")).toBeInTheDocument();
    expect(screen.getByText('元数据：{"task_type":"classification","prompt_length":42}')).toBeInTheDocument();
    expect(screen.queryByText("Image Artifacts")).not.toBeInTheDocument();
  });

  it("renders ablation variant context from request summary", () => {
    const evidence = {
      evidence_id: "case-1:modality_ablation_check:1",
      step_name: "modality_ablation_check",
      trial: 1,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 128,
        has_image: false,
        image_uri_scheme: "",
        ablation_variant: "text_only",
        ablation_modalities: ["text"]
      },
      latency_ms: 25,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [],
      image_artifacts: [],
      raw_output: "{\"conflicts\":[]}",
      judge: {
        score: 0,
        reasons: ["conflict mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Ablation Variant：text_only")).toBeInTheDocument();
    expect(screen.getByText("Ablation 模态：text")).toBeInTheDocument();
  });

  it("renders image artifact metadata for localized OCR debugging", () => {
    const evidence = {
      evidence_id: "case-1:localized_observation_request:0",
      step_name: "localized_observation_request",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 42,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 25,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      image_artifacts: [
        {
          artifact_id: "case-1:box-7:crop",
          kind: "crop_candidate",
          source_image_uri: "file:///tmp/case-1.png",
          derived_image_uri: "file:///tmp/case-1-box-7.png",
          preview_image_url: "/api/artifacts/images/case-1-box-7.png",
          region: {
            x: 12,
            y: 34,
            width: 56,
            height: 78,
            unit: "pixel",
            label: "box-7"
          }
        }
      ],
      raw_output: "{\"answers\":[]}",
      judge: {
        score: 0,
        reasons: ["box 7 mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Evidence Artifacts")).toBeInTheDocument();
    expect(screen.getByText("Artifact case-1:box-7:crop")).toBeInTheDocument();
    expect(screen.getByText("类型：crop_candidate")).toBeInTheDocument();
    expect(screen.getByText("源图片：file:///tmp/case-1.png")).toBeInTheDocument();
    expect(screen.getByText("派生图片：file:///tmp/case-1-box-7.png")).toBeInTheDocument();
    expect(screen.getByText("区域：x=12, y=34, width=56, height=78, unit=pixel, label=box-7")).toBeInTheDocument();
    expect(screen.getByAltText("Crop preview case-1:box-7:crop")).toHaveAttribute(
      "src",
      "/api/artifacts/images/case-1-box-7.png"
    );
    expect(screen.getByRole("link", { name: "打开裁剪图 case-1:box-7:crop" })).toHaveAttribute(
      "href",
      "/api/artifacts/images/case-1-box-7.png"
    );
  });

  it("shows a no-preview fallback for image artifacts without preview URLs", () => {
    const evidence = {
      evidence_id: "case-1:localized_observation_request:0",
      step_name: "localized_observation_request",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 42,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 25,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      image_artifacts: [
        {
          artifact_id: "case-1:box-8:crop",
          kind: "crop_candidate",
          source_image_uri: "file:///tmp/case-1.png",
          derived_image_uri: "",
          region: null
        }
      ],
      raw_output: "{\"answers\":[]}",
      judge: {
        score: 0,
        reasons: ["box 7 mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("预览图：无")).toBeInTheDocument();
  });

  it("renders task-native judge deltas with target ids and metadata", () => {
    const evidence = {
      evidence_id: "multimodal-case:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 128,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 45,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [],
      image_artifacts: [],
      raw_output: "{\"conflicts\":[]}",
      judge: {
        score: 0,
        reasons: ["multimodal:conflict:1 conflict_actual_mismatch"],
        deltas: [
          {
            target_id: "multimodal:conflict:1",
            expected: "image and caption both describe a cat",
            actual: "image shows dog while caption says cat",
            reason: "conflict_actual_mismatch",
            metadata: {
              field: "actual",
              conflict_type: "visual_text_conflict",
              modalities: ["image", "text"],
              confidence: 0.76
            }
          },
          {
            target_id: "video:segment:1",
            expected: "person_enters",
            actual: "person_leaves",
            reason: "segment_label_mismatch",
            metadata: {
              field: "label",
              confidence: 0.62
            }
          }
        ]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Judge Deltas")).toBeInTheDocument();
    expect(screen.getByText("目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("原因：conflict_actual_mismatch")).toBeInTheDocument();
    expect(screen.getByText("期望：image and caption both describe a cat")).toBeInTheDocument();
    expect(screen.getByText("实际：image shows dog while caption says cat")).toBeInTheDocument();
    expect(
      screen.getByText(
        '元数据：{"field":"actual","conflict_type":"visual_text_conflict","modalities":["image","text"],"confidence":0.76}'
      )
    ).toBeInTheDocument();
    expect(screen.getByText("目标：video:segment:1")).toBeInTheDocument();
    expect(screen.getByText("原因：segment_label_mismatch")).toBeInTheDocument();
  });

  it("renders structured native artifact metadata for regions, segments, and multimodal conflicts", () => {
    const evidence = {
      evidence_id: "native-artifacts:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 128,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 45,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [
        {
          artifact_id: "native-artifacts:baseline:0:image_region_1:delta",
          kind: "image_region_delta",
          artifact_type: "image_region",
          source_uri: "file:///tmp/image.png",
          derived_uri: "",
          preview_url: "",
          region: null,
          metadata: {
            target_id: "image:region:1",
            reason: "region_label_mismatch",
            expected_region: { x: 10, y: 20, width: 30, height: 40, unit: "pixel", label: "cat" },
            actual_region: { x: 10, y: 20, width: 30, height: 40, unit: "pixel", label: "dog" }
          }
        },
        {
          artifact_id: "native-artifacts:baseline:0:video_segment_1:delta",
          kind: "video_segment_delta",
          artifact_type: "video_segment",
          source_uri: "file:///tmp/video.mp4",
          derived_uri: "",
          preview_url: "",
          region: null,
          metadata: {
            target_id: "video:segment:1",
            reason: "segment_label_mismatch",
            expected_segment: { start_ms: 1000, end_ms: 2500, label: "person_enters" },
            actual_segment: { start_ms: 1000, end_ms: 2500, label: "person_leaves" }
          }
        },
        {
          artifact_id: "native-artifacts:baseline:0:multimodal_conflict_1:delta",
          kind: "multimodal_conflict_delta",
          artifact_type: "multimodal_conflict",
          source_uri: "file:///tmp/multimodal.mp4",
          derived_uri: "",
          preview_url: "",
          region: null,
          metadata: {
            target_id: "multimodal:conflict:1",
            reason: "conflict_actual_mismatch",
            expected_conflict_type: "visual_text_conflict",
            actual_conflict_type: "visual_text_conflict",
            expected_modalities: ["image", "text"],
            actual_modalities: ["image", "text"]
          }
        }
      ],
      image_artifacts: [],
      raw_output: "{\"regions\":[]}",
      judge: {
        score: 0,
        reasons: ["native mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    const artifacts = screen.getAllByLabelText("Artifact native context");
    expect(within(artifacts[0]).getByText("目标：image:region:1")).toBeInTheDocument();
    expect(within(artifacts[0]).getByText("期望区域：x=10, y=20, width=30, height=40, unit=pixel, label=cat")).toBeInTheDocument();
    expect(within(artifacts[0]).getByText("实际区域：x=10, y=20, width=30, height=40, unit=pixel, label=dog")).toBeInTheDocument();
    expect(within(artifacts[1]).getByText("目标：video:segment:1")).toBeInTheDocument();
    expect(within(artifacts[1]).getByText("期望片段：start=1000ms, end=2500ms, label=person_enters")).toBeInTheDocument();
    expect(within(artifacts[1]).getByText("实际片段：start=1000ms, end=2500ms, label=person_leaves")).toBeInTheDocument();
    expect(within(artifacts[2]).getByText("目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(within(artifacts[2]).getByText("期望模态：image, text")).toBeInTheDocument();
    expect(within(artifacts[2]).getByText("实际模态：image, text")).toBeInTheDocument();
    expect(within(artifacts[2]).getByText("冲突类型：visual_text_conflict → visual_text_conflict")).toBeInTheDocument();
  });

  it("renders video segment manifest artifacts as audit links", () => {
    const evidence = {
      evidence_id: "video-case:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 128,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 45,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [
        {
          artifact_id: "video-case:baseline:0:video_segment_1:delta",
          kind: "video_segment_delta",
          artifact_type: "video_segment",
          source_uri: "file:///tmp/video.mp4",
          derived_uri: "file:///tmp/artifacts/video-case_baseline_0_video_segment_1_delta.json",
          preview_url: "",
          region: null,
          metadata: {
            target_id: "video:segment:1",
            reason: "segment_label_mismatch",
            manifest_type: "video_segment_delta",
            expected_segment: { start_ms: 1000, end_ms: 2500, label: "person_enters" },
            actual_segment: { start_ms: 1000, end_ms: 2500, label: "person_leaves" },
            keyframe_thumbnails: [
              {
                timestamp_ms: 1000,
                preview_url: "/api/artifacts/manifests/video-case_baseline_0_video_segment_1_delta_keyframe_1000.json"
              }
            ]
          }
        }
      ],
      image_artifacts: [],
      raw_output: "{\"temporal_segments\":[]}",
      judge: {
        score: 0,
        reasons: ["video segment mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Video Segment Audit")).toBeInTheDocument();
    expect(screen.getByText("Manifest 类型：video_segment_delta")).toBeInTheDocument();
    expect(screen.getByText("审计片段：1000ms → 2500ms")).toBeInTheDocument();
    expect(screen.getByText("审计标签：person_enters → person_leaves")).toBeInTheDocument();
    expect(screen.getByText("Keyframe Thumbnails")).toBeInTheDocument();
    expect(screen.getByText("关键帧：1000ms")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "打开关键帧 thumbnail video-case:baseline:0:video_segment_1:delta 1000ms" })
    ).toHaveAttribute(
      "href",
      "/api/artifacts/manifests/video-case_baseline_0_video_segment_1_delta_keyframe_1000.json"
    );
    expect(
      screen.getByRole("link", { name: "打开视频片段 manifest video-case:baseline:0:video_segment_1:delta" })
    ).toHaveAttribute("href", "/api/artifacts/manifests/video-case_baseline_0_video_segment_1_delta.json");
  });

  it("renders multimodal conflict manifest artifacts as audit links", () => {
    const evidence = {
      evidence_id: "multimodal-case:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 128,
        has_image: true,
        image_uri_scheme: "file"
      },
      latency_ms: 45,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [
        {
          artifact_id: "multimodal-case:baseline:0:multimodal_conflict_1:delta",
          kind: "multimodal_conflict_delta",
          artifact_type: "multimodal_conflict",
          source_uri: "file:///tmp/multimodal.mp4",
          derived_uri: "file:///tmp/artifacts/multimodal-case_baseline_0_multimodal_conflict_1_delta.json",
          preview_url: "",
          region: null,
          metadata: {
            target_id: "multimodal:conflict:1",
            reason: "conflict_actual_mismatch",
            manifest_type: "multimodal_conflict_delta",
            expected: "image and caption both describe a cat",
            actual: "image shows dog while caption says cat",
            expected_modalities: ["image", "text"],
            actual_modalities: ["image", "text"],
            expected_conflict_type: "visual_text_conflict",
            actual_conflict_type: "visual_text_conflict"
          }
        }
      ],
      image_artifacts: [],
      raw_output: "{\"conflicts\":[]}",
      judge: {
        score: 0,
        reasons: ["multimodal conflict mismatch"]
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.getByText("Multimodal Conflict Audit")).toBeInTheDocument();
    expect(screen.getByText("Manifest 类型：multimodal_conflict_delta")).toBeInTheDocument();
    expect(screen.getByText("审计目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("审计模态：image, text → image, text")).toBeInTheDocument();
    expect(screen.getByText("审计结论：image and caption both describe a cat → image shows dog while caption says cat")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "打开跨模态冲突 manifest multimodal-case:baseline:0:multimodal_conflict_1:delta"
      })
    ).toHaveAttribute(
      "href",
      "/api/artifacts/manifests/multimodal-case_baseline_0_multimodal_conflict_1_delta.json"
    );
  });

  it("hides judge deltas section when no structured deltas are present", () => {
    const evidence = {
      evidence_id: "classification-case:baseline_replay:0",
      step_name: "baseline_replay",
      trial: 0,
      model_name: "ark-seed2-lite",
      model_provider: "ark",
      model_id: "ep-seed2-lite",
      request_summary: {
        prompt_length: 64,
        has_image: false,
        image_uri_scheme: ""
      },
      latency_ms: 30,
      response_parse_error: "",
      model_call_error_type: "",
      model_call_error_message: "",
      artifacts: [],
      image_artifacts: [],
      raw_output: "{\"label\":\"positive\"}",
      judge: {
        score: 1,
        reasons: [],
        deltas: []
      }
    } satisfies ExperimentEvidence;

    render(<EvidenceDetail evidence={evidence} />);

    expect(screen.queryByText("Judge Deltas")).not.toBeInTheDocument();
  });
});

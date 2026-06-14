import { cleanup, render, screen } from "@testing-library/react";
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

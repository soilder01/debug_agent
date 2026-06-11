import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ExperimentEvidence } from "../api/client";
import { EvidenceDetail } from "./EvidenceDetail";

afterEach(() => {
  cleanup();
});

describe("EvidenceDetail", () => {
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

    expect(screen.getByText("Image Artifacts")).toBeInTheDocument();
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
});

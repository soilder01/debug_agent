import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { DebugReport } from "../api/client";
import { ReportPanel } from "./ReportPanel";

afterEach(() => {
  cleanup();
});

describe("ReportPanel", () => {
  it("renders image artifact summary from experiment evidence", () => {
    const report: DebugReport = {
      job_id: "job-1",
      case_id: "case-1",
      status: "needs_human_review",
      observed_failure: {
        type: "ocr_mismatch",
        summary: "box 7 mismatch",
        affected_box_ids: [7]
      },
      planned_experiments: ["localized_observation_request"],
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["case-1:localized_observation_request:0"],
        image_artifact_ids: ["case-1:box-7:localized-candidate"]
      },
      root_cause: {
        label: "erasure_revision_failure",
        confidence: "medium",
        evidence_summary: "需要查看局部作答区域。"
      },
      suggested_sheet_fields: {
        错误原因: "局部识别失败"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("可视证据：1")).toBeInTheDocument();
    expect(screen.getByText("case-1:box-7:localized-candidate")).toBeInTheDocument();
  });

  it("renders replay stability metrics from experiment summary", () => {
    const report: DebugReport = {
      job_id: "job-1",
      case_id: "case-1",
      status: "needs_human_review",
      observed_failure: {
        type: "ocr_mismatch",
        summary: "box 7 mismatch",
        affected_box_ids: [7]
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: {
        total_trials: 5,
        success_count: 2,
        failed_trial_count: 3,
        success_rate: 0.4,
        stability_label: "unstable",
        evidence_ids: ["e1", "e2", "e3", "e4", "e5"],
        image_artifact_ids: []
      },
      root_cause: {
        label: "unstable_handwriting_recognition",
        confidence: "medium",
        evidence_summary: "五次复测中存在波动。"
      },
      suggested_sheet_fields: {
        错误原因: "模型不稳定"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("复测稳定性：unstable")).toBeInTheDocument();
    expect(screen.getByText("复测通过率：40%")).toBeInTheDocument();
    expect(screen.getByText("失败次数：3/5")).toBeInTheDocument();
  });
});

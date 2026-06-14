import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DebugReport } from "../api/client";
import { ReportPanel } from "./ReportPanel";

afterEach(() => {
  cleanup();
});

describe("ReportPanel", () => {
  it("renders generic artifact summary from experiment evidence", () => {
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
        artifact_ids: ["case-1:localized_observation_request:0:input-snapshot"],
        image_artifact_ids: ["case-1:box-7:localized-candidate"]
      },
      root_cause: {
        label: "erasure_revision_failure",
        confidence: "medium",
        evidence_summary: "需要查看局部作答区域。"
      },
      evidence_citations: [
        {
          evidence_id: "case-1:localized_observation_request:0",
          step_name: "localized_observation_request",
          box_id: 7,
          reason: "student_answer_mismatch",
          artifact_ids: ["case-1:box-7:localized-candidate"]
        }
      ],
      suggested_sheet_fields: {
        错误原因: "局部识别失败"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("Evidence Artifacts")).toBeInTheDocument();
    expect(screen.getByText("证据产物：1")).toBeInTheDocument();
    expect(screen.getByText("case-1:localized_observation_request:0:input-snapshot")).toBeInTheDocument();
    expect(screen.getByText("Evidence Citations")).toBeInTheDocument();
    expect(screen.getByText("引用证据：case-1:localized_observation_request:0")).toBeInTheDocument();
    expect(screen.getByText("引用步骤：localized_observation_request")).toBeInTheDocument();
    expect(screen.getByText("引用目标/区域：7")).toBeInTheDocument();
    expect(screen.getByText("引用原因：student_answer_mismatch")).toBeInTheDocument();
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

  it("renders experiment step trajectory summaries", () => {
    const report: DebugReport = {
      job_id: "job-trajectory",
      case_id: "case-trajectory",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "native mismatch",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay", "modality_ablation_check"],
      experiment_summary: {
        total_trials: 3,
        success_count: 1,
        failed_trial_count: 2,
        success_rate: 1 / 3,
        stability_label: "unstable",
        evidence_ids: ["e-baseline-pass", "e-baseline-fail", "e-ablation-fail"],
        artifact_ids: ["baseline:input", "baseline:delta", "ablation:delta"],
        image_artifact_ids: [],
        step_summaries: [
          {
            step_name: "baseline_replay",
            total_trials: 2,
            success_count: 1,
            failed_trial_count: 1,
            success_rate: 0.5,
            delta_reasons: ["region_label_mismatch"],
            target_ids: ["image:region:1"],
            evidence_ids: ["e-baseline-pass", "e-baseline-fail"],
            artifact_ids: ["baseline:input", "baseline:delta"],
            ablation_variants: ["image_only"],
            ablation_modalities: ["image"]
          },
          {
            step_name: "modality_ablation_check",
            total_trials: 1,
            success_count: 0,
            failed_trial_count: 1,
            success_rate: 0,
            delta_reasons: ["conflict_actual_mismatch"],
            target_ids: ["multimodal:conflict:1"],
            evidence_ids: ["e-ablation-fail"],
            artifact_ids: ["ablation:delta"]
          }
        ]
      },
      root_cause: {
        label: "output_mismatch",
        confidence: "high",
        evidence_summary: "step comparison found different failures."
      },
      suggested_sheet_fields: {
        错误原因: "结构化差异"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("Experiment Trajectory")).toBeInTheDocument();
    expect(screen.getByText("步骤：baseline_replay")).toBeInTheDocument();
    expect(screen.getByText("步骤通过率：50%")).toBeInTheDocument();
    expect(screen.getByText("步骤失败次数：1/2")).toBeInTheDocument();
    expect(screen.getByText("Delta 类型：region_label_mismatch")).toBeInTheDocument();
    expect(screen.getByText("目标：image:region:1")).toBeInTheDocument();
    expect(screen.getByText("Ablation：image_only")).toBeInTheDocument();
    expect(screen.getByText("Ablation 模态：image")).toBeInTheDocument();
    expect(screen.getByText("证据：e-baseline-pass, e-baseline-fail")).toBeInTheDocument();
    expect(screen.getByText("产物：baseline:input, baseline:delta")).toBeInTheDocument();
    expect(screen.getByText("步骤：modality_ablation_check")).toBeInTheDocument();
    expect(screen.getByText("Delta 类型：conflict_actual_mismatch")).toBeInTheDocument();
    expect(screen.getByText("目标：multimodal:conflict:1")).toBeInTheDocument();
  });

  it("selects evidence from experiment trajectory summaries", async () => {
    const onSelectEvidence = vi.fn();
    const report: DebugReport = {
      job_id: "job-trajectory",
      case_id: "case-trajectory",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "native mismatch",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["e-ablation-fail"],
        artifact_ids: ["ablation:delta"],
        image_artifact_ids: [],
        step_summaries: [
          {
            step_name: "modality_ablation_check",
            total_trials: 1,
            success_count: 0,
            failed_trial_count: 1,
            success_rate: 0,
            delta_reasons: ["conflict_actual_mismatch"],
            target_ids: ["multimodal:conflict:1"],
            evidence_ids: ["e-ablation-fail"],
            artifact_ids: ["ablation:delta"]
          }
        ]
      },
      root_cause: {
        label: "output_mismatch",
        confidence: "high",
        evidence_summary: "trajectory links evidence."
      },
      suggested_sheet_fields: {
        错误原因: "结构化差异"
      }
    };

    render(<ReportPanel report={report} onSelectEvidence={onSelectEvidence} />);

    await userEvent.click(screen.getByRole("button", { name: "e-ablation-fail" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("e-ablation-fail");
  });

  it("highlights ablation diagnosis fields", () => {
    const report: DebugReport = {
      job_id: "job-ablation-root-cause",
      case_id: "case-ablation-root-cause",
      status: "needs_human_review",
      observed_failure: {
        type: "cross_modal_alignment_failure",
        summary: "single modality passed while cross-modal compare failed",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: {
        total_trials: 3,
        success_count: 2,
        failed_trial_count: 1,
        success_rate: 2 / 3,
        stability_label: "unstable",
        evidence_ids: ["e-image-only", "e-text-only", "e-cross-modal"],
        image_artifact_ids: []
      },
      root_cause: {
        label: "cross_modal_alignment_failure",
        confidence: "high",
        evidence_summary: "single-modality variants passed; cross-modal variant failed."
      },
      root_cause_trace: [
        {
          step_name: "modality_ablation_check",
          variant: "cross_modal_compare",
          modalities: ["image", "text"],
          evidence_id: "e-cross-modal",
          judge_score: 0,
          delta_reasons: ["conflict_actual_mismatch"],
          target_ids: ["multimodal:conflict:1"],
          artifact_ids: ["ablation:delta"]
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题：单模态可通过，但跨模态比较失败。",
        Ablation结论: "单模态变体 image_only, text_only 可通过，但跨模态变体 cross_modal_compare 失败。"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("Ablation Diagnosis")).toBeInTheDocument();
    const diagnosis = within(screen.getByLabelText("Ablation diagnosis"));
    expect(
      diagnosis.getByText("单模态变体 image_only, text_only 可通过，但跨模态变体 cross_modal_compare 失败。")
    ).toBeInTheDocument();
    expect(screen.getByText("Root Cause Trace")).toBeInTheDocument();
    expect(screen.getByText("变体：cross_modal_compare")).toBeInTheDocument();
    expect(screen.getByText("模态：image, text")).toBeInTheDocument();
    expect(screen.getByText("证据：e-cross-modal")).toBeInTheDocument();
    expect(screen.getByText("Delta：conflict_actual_mismatch")).toBeInTheDocument();
    expect(screen.getByText("目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("产物：ablation:delta")).toBeInTheDocument();
  });
});

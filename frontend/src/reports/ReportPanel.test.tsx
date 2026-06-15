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

  it("selects evidence from citation artifact links", async () => {
    const onSelectEvidence = vi.fn();
    const report: DebugReport = {
      job_id: "job-citation-artifacts",
      case_id: "case-citation-artifacts",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "citation artifact mismatch",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["citation-evidence-1"],
        artifact_ids: ["citation:video_segment_1:delta"],
        image_artifact_ids: []
      },
      root_cause: {
        label: "output_mismatch",
        confidence: "high",
        evidence_summary: "citation artifact should open evidence."
      },
      evidence_citations: [
        {
          evidence_id: "citation-evidence-1",
          step_name: "baseline_replay",
          box_id: null,
          reason: "segment_label_mismatch",
          artifact_ids: ["citation:video_segment_1:delta"]
        }
      ],
      suggested_sheet_fields: {
        错误原因: "视频片段差异"
      }
    };

    render(<ReportPanel report={report} onSelectEvidence={onSelectEvidence} />);

    await userEvent.click(screen.getByRole("button", { name: "Open artifact citation:video_segment_1:delta" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("citation-evidence-1");
  });

  it("selects evidence from global artifact summary links when ownership is known", async () => {
    const onSelectEvidence = vi.fn();
    const report: DebugReport = {
      job_id: "job-global-artifact-links",
      case_id: "case-global-artifact-links",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "global artifact mismatch",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["global-artifact-evidence-1"],
        artifact_ids: ["global:video_segment_1:delta"],
        artifact_evidence_links: [
          {
            artifact_id: "global:video_segment_1:delta",
            evidence_id: "global-artifact-evidence-1"
          }
        ],
        image_artifact_ids: []
      },
      root_cause: {
        label: "output_mismatch",
        confidence: "high",
        evidence_summary: "global artifact should open evidence."
      },
      suggested_sheet_fields: {
        错误原因: "视频片段差异"
      }
    };

    render(<ReportPanel report={report} onSelectEvidence={onSelectEvidence} />);

    await userEvent.click(screen.getByRole("button", { name: "Open artifact global:video_segment_1:delta" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("global-artifact-evidence-1");
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

  it("selects evidence from report artifact links", async () => {
    const onSelectEvidence = vi.fn();
    const report: DebugReport = {
      job_id: "job-artifact-links",
      case_id: "case-artifact-links",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "native artifact mismatch",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["evidence-with-artifacts"],
        artifact_ids: [
          "case-artifact-links:baseline_replay:0:video_segment_1:delta",
          "case-artifact-links:baseline_replay:0:multimodal_conflict_1:delta"
        ],
        image_artifact_ids: [],
        step_summaries: [
          {
            step_name: "baseline_replay",
            total_trials: 1,
            success_count: 0,
            failed_trial_count: 1,
            success_rate: 0,
            delta_reasons: ["segment_label_mismatch"],
            target_ids: ["video:segment:1"],
            evidence_ids: ["evidence-with-artifacts"],
            artifact_ids: ["case-artifact-links:baseline_replay:0:video_segment_1:delta"]
          }
        ]
      },
      root_cause: {
        label: "output_mismatch",
        confidence: "high",
        evidence_summary: "artifact links should open evidence detail."
      },
      root_cause_trace: [
        {
          step_name: "baseline_replay",
          variant: "video_only",
          modalities: ["video"],
          evidence_id: "trace-evidence",
          judge_score: 0,
          delta_reasons: ["segment_label_mismatch"],
          target_ids: ["video:segment:1"],
          artifact_ids: ["trace:video_segment_1:delta"]
        }
      ],
      suggested_sheet_fields: {
        错误原因: "视频片段差异"
      }
    };

    render(<ReportPanel report={report} onSelectEvidence={onSelectEvidence} />);

    await userEvent.click(
      screen.getByRole("button", {
        name: "Open artifact case-artifact-links:baseline_replay:0:video_segment_1:delta"
      })
    );
    await userEvent.click(screen.getByRole("button", { name: "Open artifact trace:video_segment_1:delta" }));

    expect(onSelectEvidence).toHaveBeenNthCalledWith(1, "evidence-with-artifacts");
    expect(onSelectEvidence).toHaveBeenNthCalledWith(2, "trace-evidence");
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
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "pending",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        },
        {
          category: "model_capability",
          priority: "high",
          status: "pending",
          summary: "将跨模态融合短板纳入模型能力归因。",
          detail: "单模态通过但跨模态失败，优先检查 fusion/alignment 能力。"
        }
      ],
      confidence_reasons: [
        {
          source: "evidence_count",
          level: "high",
          summary: "3 条 evidence 支撑当前判断。"
        },
        {
          source: "ablation_pattern",
          level: "high",
          summary: "root cause trace 包含 cross_modal_compare 变体，支持跨模态归因。"
        },
        {
          source: "verification_outcome",
          level: "neutral",
          summary: "尚无验证任务结果参与置信度判断。"
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
    expect(screen.getByText("Recommended Actions")).toBeInTheDocument();
    expect(screen.getByText("prompt/high：强化跨模态对比步骤。")).toBeInTheDocument();
    expect(screen.getAllByText("状态：pending")[0]).toBeInTheDocument();
    expect(screen.getByText("要求模型先分别列出 image/text 证据，再输出冲突结论。")).toBeInTheDocument();
    expect(screen.getByText("model_capability/high：将跨模态融合短板纳入模型能力归因。")).toBeInTheDocument();
    expect(screen.getByText("Confidence Reasons")).toBeInTheDocument();
    expect(screen.getByText("evidence_count/high：3 条 evidence 支撑当前判断。")).toBeInTheDocument();
    expect(
      screen.getByText("ablation_pattern/high：root cause trace 包含 cross_modal_compare 变体，支持跨模态归因。")
    ).toBeInTheDocument();
    expect(screen.getByText("verification_outcome/neutral：尚无验证任务结果参与置信度判断。")).toBeInTheDocument();
  });

  it("delegates recommended action status updates", async () => {
    const onUpdateRecommendedActionStatus = vi.fn();
    const report: DebugReport = {
      job_id: "job-action-status",
      case_id: "case-action-status",
      status: "needs_human_review",
      observed_failure: {
        type: "cross_modal_alignment_failure",
        summary: "cross-modal compare failed",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: null,
      root_cause: {
        label: "cross_modal_alignment_failure",
        confidence: "high",
        evidence_summary: "cross-modal variant failed."
      },
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "pending",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(
      <ReportPanel report={report} onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus} />
    );

    await userEvent.click(screen.getByRole("button", { name: "Accept recommended action 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Reject recommended action 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Mark recommended action 1 applied" }));

    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(1, 0, "accepted");
    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(2, 0, "rejected");
    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(3, 0, "applied");
  });

  it("delegates verification reruns for applied recommended actions", async () => {
    const onVerifyRecommendedAction = vi.fn();
    const report: DebugReport = {
      job_id: "job-action-verify",
      case_id: "case-action-verify",
      status: "needs_human_review",
      observed_failure: {
        type: "cross_modal_alignment_failure",
        summary: "cross-modal compare failed",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: null,
      root_cause: {
        label: "cross_modal_alignment_failure",
        confidence: "high",
        evidence_summary: "cross-modal variant failed."
      },
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "applied",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(<ReportPanel report={report} onVerifyRecommendedAction={onVerifyRecommendedAction} />);

    await userEvent.click(screen.getByRole("button", { name: "Verify recommended action 1" }));

    expect(onVerifyRecommendedAction).toHaveBeenCalledWith(0);
  });

  it("renders recommended action status event audit", () => {
    const report: DebugReport = {
      job_id: "job-action-events",
      case_id: "case-action-events",
      status: "needs_human_review",
      observed_failure: {
        type: "cross_modal_alignment_failure",
        summary: "cross-modal compare failed",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: null,
      root_cause: {
        label: "cross_modal_alignment_failure",
        confidence: "high",
        evidence_summary: "cross-modal variant failed."
      },
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "accepted",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(
      <ReportPanel
        report={report}
        recommendedActionStatusEvents={[
          {
            event_id: 7,
            job_id: "job-action-events",
            action_index: 0,
            status: "accepted",
            actor: "qa-reviewer",
            note: "approved prompt update",
            created_at: "2026-06-14T00:00:01+00:00"
          }
        ]}
      />
    );

    expect(screen.getByText("Recommended Action Status Events")).toBeInTheDocument();
    expect(screen.getByText("操作 1：accepted")).toBeInTheDocument();
    expect(screen.getByText("操作者：qa-reviewer")).toBeInTheDocument();
    expect(screen.getByText("备注：approved prompt update")).toBeInTheDocument();
    expect(screen.getByText("时间：2026-06-14T00:00:01+00:00")).toBeInTheDocument();
  });

  it("renders recommended action verification job links", () => {
    const report: DebugReport = {
      job_id: "job-action-verifications",
      case_id: "case-action-verifications",
      status: "needs_human_review",
      observed_failure: {
        type: "cross_modal_alignment_failure",
        summary: "cross-modal compare failed",
        affected_box_ids: []
      },
      planned_experiments: ["modality_ablation_check"],
      experiment_summary: null,
      root_cause: {
        label: "cross_modal_alignment_failure",
        confidence: "high",
        evidence_summary: "cross-modal variant failed."
      },
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "applied",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(
      <ReportPanel
        report={report}
        recommendedActionVerifications={[
          {
            job_id: "job-action-verifications",
            action_index: 0,
            verification_job_id: "job-verify-1",
            actor: "qa-reviewer",
            note: "verify prompt fix",
            created_at: "2026-06-14T00:00:02+00:00"
          }
        ]}
        recommendedActionVerificationResults={[
          {
            job_id: "job-action-verifications",
            action_index: 0,
            verification_job_id: "job-verify-1",
            result: "resolved",
            source_success_rate: 0.5,
            verification_success_rate: 1,
            source_root_cause: "single_modality_capability_gap",
            verification_root_cause: "output_mismatch",
            summary: "验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。"
          }
        ]}
      />
    );

    expect(screen.getByText("Recommended Action Verification Jobs")).toBeInTheDocument();
    expect(screen.getByText("操作 1 验证任务：job-verify-1")).toBeInTheDocument();
    expect(screen.getByText("操作者：qa-reviewer")).toBeInTheDocument();
    expect(screen.getByText("备注：verify prompt fix")).toBeInTheDocument();
    expect(screen.getByText("验证结果：resolved")).toBeInTheDocument();
    expect(screen.getByText("验证通过率：100%｜原通过率：50%")).toBeInTheDocument();
    expect(screen.getByText("验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。")).toBeInTheDocument();
  });
});

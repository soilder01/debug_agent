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

    expect(screen.getByRole("region", { name: "根因分析" })).toHaveClass("root-cause-panel");
    expect(screen.getByLabelText("证据产物列表")).toHaveClass("evidence-spine");
    expect(screen.getByRole("heading", { name: "证据产物" })).toBeInTheDocument();
    expect(screen.getByText("证据产物：1")).toBeInTheDocument();
    expect(screen.getByText("case-1:localized_observation_request:0:input-snapshot")).toBeInTheDocument();
    expect(screen.getByText("证据引用")).toBeInTheDocument();
    expect(screen.getByText("引用证据：case-1:localized_observation_request:0")).toBeInTheDocument();
    expect(screen.getByText("引用步骤：localized_observation_request")).toBeInTheDocument();
    expect(screen.getByText("引用目标/区域：7")).toBeInTheDocument();
    expect(screen.getByText("引用原因：student_answer_mismatch")).toBeInTheDocument();
  });

  it("renders product summary labels instead of raw report taxonomy", () => {
    const report: DebugReport = {
      job_id: "job-product",
      case_id: "case-product",
      status: "needs_human_review",
      product_summary: {
        root_cause_label: "模型时序输出不稳定 / 高置信",
        failure_summary: "同一视频片段多次输出不一致。",
        evidence_source: "4 次 baseline/实验 evidence、定向深挖任务",
        confidence_explanation: "高置信；4 条 evidence 支撑当前判断。",
        next_action: "P0：补充时间窗约束后重跑验证"
      },
      observed_failure: {
        type: "video_timestamp_mismatch",
        summary: "同一视频片段多次输出不一致。",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: {
        total_trials: 4,
        success_count: 1,
        failed_trial_count: 3,
        success_rate: 0.25,
        stability_label: "unstable",
        evidence_ids: ["e-1"]
      },
      root_cause: {
        label: "model_instability",
        confidence: "high",
        evidence_summary: "baseline 多次复测不稳定。"
      },
      suggested_sheet_fields: {
        错误原因: "模型时序输出不稳定"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByText("类型：模型时序输出不稳定 / 高置信")).toBeInTheDocument();
    expect(screen.queryByText("类型：model_instability")).not.toBeInTheDocument();
    expect(screen.getByText("证据来源：4 次 baseline/实验 evidence、定向深挖任务")).toBeInTheDocument();
    expect(screen.getByText("下一步：P0：补充时间窗约束后重跑验证")).toBeInTheDocument();
  });

  it("renders action queue as stateful follow-up actions", () => {
    const report: DebugReport = {
      job_id: "job-action-queue",
      case_id: "case-action-queue",
      status: "needs_human_review",
      observed_failure: {
        type: "video_timestamp_mismatch",
        summary: "同一视频片段多次输出不一致。",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: null,
      root_cause: {
        label: "model_instability",
        confidence: "high",
        evidence_summary: "baseline 多次复测不稳定。"
      },
      action_queue: [
        {
          id: "recommended:0",
          kind: "recommended_action",
          title: "补充视频时间窗约束后重跑验证。",
          detail: "在 prompt 中补充 2s-4s 时间窗。",
          priority: "P0",
          state: "verifying",
          state_label: "验证中",
          source: "stability",
          source_ref: "report.recommended_actions[0]",
          owner: "case-owner",
          status: "applied",
          status_updated_at: "2026-06-26T12:00:00Z",
          verification_job_id: "job-verify-1",
          verification_result: "pending",
          verification_summary: "推荐动作验证任务尚未完成。",
          writeback_status: "succeeded",
          writeback_row_id: "row-42",
          writeback_report_url: "https://debug-agent.local/jobs/job-action-queue/report",
          evidence_ids: "e-1",
          artifact_ids: "artifact-1",
          trace_refs: "baseline_replay",
          available_operations: ["accept", "verify", "writeback", "manual_handoff"],
          next_operation: "等待验证任务完成"
        }
      ],
      recommended_actions: [
        {
          category: "stability",
          priority: "P0",
          status: "applied",
          summary: "补充视频时间窗约束后重跑验证。",
          detail: "在 prompt 中补充 2s-4s 时间窗。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "模型时序输出不稳定"
      }
    };
    const onVerifyRecommendedAction = vi.fn();
    const onUpdateRecommendedActionStatus = vi.fn();

    render(
      <ReportPanel
        report={report}
        onVerifyRecommendedAction={onVerifyRecommendedAction}
        onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus}
      />
    );

    expect(screen.getByRole("heading", { name: "Action Queue" })).toBeInTheDocument();
    expect(screen.getByText("P0 / 验证中：补充视频时间窗约束后重跑验证。")).toBeInTheDocument();
    expect(screen.getByText("负责人：case-owner")).toBeInTheDocument();
    expect(screen.getByText("验证任务：job-verify-1 / pending")).toBeInTheDocument();
    expect(screen.getByText("写回：succeeded / row-42")).toBeInTheDocument();
    expect(screen.getByText("下一步：等待验证任务完成")).toBeInTheDocument();
    expect(screen.getByText("来源：stability / report.recommended_actions[0]")).toBeInTheDocument();
  });

  it("renders DebugRunView as the unified runtime state source", () => {
    const report: DebugReport = {
      job_id: "job-run-view",
      case_id: "case-run-view",
      status: "completed",
      run_view: {
        job: {
          job_id: "job-run-view",
          case_id: "case-run-view",
          status: "completed",
          status_label: "已完成",
          created_at: "2026-06-26T12:00:00Z",
          updated_at: "2026-06-26T12:05:00Z"
        },
        summary: {
          headline: "Debug 任务已完成",
          current_phase: "auto_closure",
          next_step: "确认报告后执行写回。",
          evidence_count: 2,
          agent_trace_count: 1
        },
        timeline: [
          {
            key: "auto_closure",
            label: "自动闭环",
            status: "completed",
            status_label: "已完成",
            summary: "auto closure completed",
            started_at: "2026-06-26T12:04:00Z",
            updated_at: "2026-06-26T12:05:00Z"
          }
        ],
        agent_traces: [
          {
            agent_role: "report_root_cause",
            reasoning_summary: "多轮复测显示模型时序输出不稳定。"
          }
        ],
        auto_closure: {
          status: "completed",
          status_label: "已完成",
          summary: "auto closure completed",
          stage_count: 1
        },
        debug_loop: {
          status: "completed",
          status_label: "已完成",
          summary: "第 1 轮探索已找到 verified root cause；prompt probe supported.",
          current_iteration: 1,
          decision: "verified_root_cause_found",
          next_action: "查看已验证根因并决定是否同步报告。",
          stop_reason: "prompt probe supported.",
          iterations: [
            {
              iteration: 1,
              decision: "verified_root_cause_found",
              pending_probe_count: 0,
              completed_probe_count: 1,
              supported_comparison_count: 1
            }
          ]
        },
        hypothesis_closure: {
          status: "completed",
          status_label: "已完成",
          summary: "已生成 1 个候选假设、1 个 probe 计划、1 个因果比较；prompt probe 已完成。",
          hypothesis_count: 1,
          probe_plan_count: 1,
          probe_result_count: 1,
          causal_comparison_count: 1,
          verified_root_cause_count: 1,
          unverified_hypothesis_count: 0,
          fairness_lock: {
            model_runner_config_ref: "locked_source"
          },
          hypotheses: [
            {
              hypothesis_id: "h-prompt",
              category: "prompt_constraint",
              claim: "原 prompt 没有强制要求描述右臂和双臂配合。",
              status: "candidate"
            }
          ],
          probe_plans: [
            {
              probe_id: "probe-h-prompt",
              hypothesis_id: "h-prompt",
              intervention_type: "prompt_patch",
              model_runner_config_ref: "locked_source"
            }
          ],
          probe_results: [
            {
              probe_id: "probe-h-prompt",
              hypothesis_id: "h-prompt",
              status: "completed",
              probe_job_id: "job-probe-h-prompt",
              evidence_ids: ["job-probe-h-prompt:success"]
            }
          ],
          causal_comparisons: [
            {
              hypothesis_id: "h-prompt",
              probe_id: "probe-h-prompt",
              verdict: "supported",
              delta: 1
            }
          ],
          verified_root_causes: [
            {
              hypothesis_id: "h-prompt",
              probe_id: "probe-h-prompt",
              summary: "Prompt patch improved success rate with locked source runner."
            }
          ],
          unverified_hypotheses: []
        },
        writeback: {
          status: "succeeded",
          status_label: "成功",
          row_id: "row-42",
          report_url: "https://debug-agent.local/jobs/job-run-view/report",
          error_message: "",
          updated_at: "2026-06-26T12:06:00Z"
        },
        action_queue: {
          summary: { total: 1, verified: 1 },
          items: [
            {
              id: "recommended:0",
              kind: "recommended_action",
              title: "补充视频时间窗约束后重跑验证。",
              detail: "",
              priority: "P0",
              state: "verified",
              state_label: "已通过",
              source: "prompt",
              source_ref: "report.recommended_actions[0]",
              owner: "case-owner",
              status: "applied",
              status_updated_at: "2026-06-26T12:03:00Z",
              verification_job_id: "job-verify-1",
              verification_result: "resolved",
              verification_summary: "推荐操作可能已修复该问题。",
              writeback_status: "succeeded",
              writeback_row_id: "row-42",
              writeback_report_url: "https://debug-agent.local/jobs/job-run-view/report",
              evidence_ids: "e-1",
              artifact_ids: "",
              trace_refs: "",
              available_operations: ["verify", "writeback", "manual_handoff"],
              next_operation: "已验证通过并写回，可以沉淀修复结论。"
            }
          ]
        }
      },
      observed_failure: {
        type: "video_timestamp_mismatch",
        summary: "同一视频片段多次输出不一致。",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: null,
      root_cause: {
        label: "model_instability",
        confidence: "high",
        evidence_summary: "baseline 多次复测不稳定。"
      },
      suggested_sheet_fields: {
        错误原因: "模型时序输出不稳定"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByRole("heading", { name: "DebugRunView" })).toBeInTheDocument();
    expect(screen.getByText("统一状态：Debug 任务已完成")).toBeInTheDocument();
    expect(screen.getByText("下一步：确认报告后执行写回。")).toBeInTheDocument();
    expect(screen.getByText("自动闭环：已完成｜auto closure completed")).toBeInTheDocument();
    expect(screen.getByText("写回：成功｜row-42")).toBeInTheDocument();
    expect(screen.getByText("循环探索：第 1 轮｜verified_root_cause_found")).toBeInTheDocument();
    expect(screen.getByText("循环下一步：查看已验证根因并决定是否同步报告。")).toBeInTheDocument();
    expect(screen.getByText("循环摘要：第 1 轮探索已找到 verified root cause；prompt probe supported.")).toBeInTheDocument();
    expect(screen.getByLabelText("Debug Loop Iterations")).toBeInTheDocument();
    expect(screen.getByText("循环轮次：第 1 轮 / verified_root_cause_found / pending=0 / completed=1 / supported=1")).toBeInTheDocument();
    expect(screen.getByText("假设闭环：已完成｜已生成 1 个候选假设、1 个 probe 计划、1 个因果比较；prompt probe 已完成。")).toBeInTheDocument();
    expect(screen.getByText("候选假设：1｜Probe 计划：1｜因果比较：1｜已验证根因：1")).toBeInTheDocument();
    expect(screen.getByText("公平性锁：locked_source")).toBeInTheDocument();
    expect(screen.getByLabelText("Hypothesis Matrix")).toBeInTheDocument();
    expect(screen.getByText("h-prompt / prompt_constraint / candidate：原 prompt 没有强制要求描述右臂和双臂配合。")).toBeInTheDocument();
    expect(screen.getByText("probe-h-prompt / prompt_patch / locked_source")).toBeInTheDocument();
    expect(screen.getByText("probe-h-prompt：supported｜delta=1")).toBeInTheDocument();
    expect(screen.getByText("Probe 结果：probe-h-prompt / completed / job-probe-h-prompt")).toBeInTheDocument();
    expect(screen.getByText("已验证根因：h-prompt / probe-h-prompt：Prompt patch improved success rate with locked source runner.")).toBeInTheDocument();
    expect(screen.getByText("auto_closure：已完成｜auto closure completed")).toBeInTheDocument();
    expect(screen.getByText("report_root_cause：多轮复测显示模型时序输出不稳定。")).toBeInTheDocument();
  });

  it("renders meta agent execution telemetry", () => {
    const report: DebugReport = {
      job_id: "job-meta",
      case_id: "case-meta",
      status: "needs_human_review",
      observed_failure: {
        type: "output_mismatch",
        summary: "failed",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: null,
      root_cause: {
        label: "schema_drift",
        confidence: "medium",
        evidence_summary: "rule fallback plus meta agent."
      },
      meta_agent_enrichment: {
        status: "completed",
        telemetry: [
          {
            agent_role: "report_root_cause",
            status: "completed",
            model_id: "seed2-pro",
            model_name: "Seed2 Pro",
            mode: "",
            thinking: "enabled",
            latency_ms: 123,
            error_message: ""
          }
        ]
      },
      judge_comparison_notes: [
        {
          evidence_id: "e-judge-1",
          target_id: "label",
          deterministic_reason: "label_mismatch",
          llm_note: "Label mismatch is consistent with schema drift.",
          risk: "medium"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "schema drift"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByLabelText("Meta Agent 执行记录")).toBeInTheDocument();
    expect(screen.getByText("report_root_cause/completed：seed2-pro")).toBeInTheDocument();
    expect(screen.getByText("thinking=enabled · mode=默认 · latency=123ms")).toBeInTheDocument();
    expect(screen.getByLabelText("Judge Comparator 辅助备注")).toBeInTheDocument();
    expect(screen.getByText("模型辅助备注：Label mismatch is consistent with schema drift.")).toBeInTheDocument();
  });

  it("renders evaluation asset diagnostics", () => {
    const report: DebugReport = {
      job_id: "job-asset-diagnostics",
      case_id: "case-asset-diagnostics",
      status: "needs_human_review",
      observed_failure: {
        type: "evaluation_asset_issue",
        summary: "评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: null,
      root_cause: {
        label: "scoring_standard_issue",
        confidence: "high",
        evidence_summary: "评分标准缺失：请补充 exact match、可接受别字/格式、box_id 对齐等规则。"
      },
      evaluation_asset_diagnostics: [
        {
          source: "prompt",
          status: "pass",
          severity: "info",
          summary: "Prompt 已要求结构化 JSON 输出。",
          recommendation: "保持 prompt 中明确的输出 schema、证据引用和约束条件。",
          evidence_ids: "e-asset-diagnostic",
          artifact_ids: "asset:prompt-snapshot",
          trace_refs: "baseline_replay:prompt_check"
        },
        {
          source: "scoring_standard",
          status: "fail",
          severity: "high",
          summary: "评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
          recommendation: "补充 exact match、可接受别字/格式、box_id 对齐等评分规则。",
          evidence_ids: "e-asset-diagnostic",
          artifact_ids: "",
          trace_refs: ""
        }
      ],
      suggested_sheet_fields: {
        错误原因: "评测资产问题：评分标准缺失"
      }
    };

    render(<ReportPanel report={report} />);

    expect(screen.getByLabelText("评估资产诊断")).toHaveClass("evidence-spine");
    expect(screen.getByText("评估资产诊断")).toBeInTheDocument();
    expect(screen.getByText("prompt/pass/info")).toBeInTheDocument();
    expect(screen.getByText("Prompt 已要求结构化 JSON 输出。")).toBeInTheDocument();
    expect(screen.getByText("建议：保持 prompt 中明确的输出 schema、证据引用和约束条件。")).toBeInTheDocument();
    expect(screen.getAllByText("引用证据：e-asset-diagnostic").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("引用产物：asset:prompt-snapshot")).toBeInTheDocument();
    expect(screen.getByText("Trace：baseline_replay:prompt_check")).toBeInTheDocument();
    expect(screen.getByText("scoring_standard/fail/high")).toBeInTheDocument();
    expect(screen.getByText("评分标准缺失，当前 0/1 结论缺少可审计的判分依据。")).toBeInTheDocument();
    expect(screen.getByText("建议：补充 exact match、可接受别字/格式、box_id 对齐等评分规则。")).toBeInTheDocument();
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

    await userEvent.click(screen.getByRole("button", { name: "打开证据产物 citation:video_segment_1:delta" }));

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

    await userEvent.click(screen.getByRole("button", { name: "打开证据产物 global:video_segment_1:delta" }));

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

    expect(screen.getByText("实验轨迹")).toBeInTheDocument();
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
        name: "打开证据产物 case-artifact-links:baseline_replay:0:video_segment_1:delta"
      })
    );
    await userEvent.click(screen.getByRole("button", { name: "打开证据产物 trace:video_segment_1:delta" }));

    expect(onSelectEvidence).toHaveBeenNthCalledWith(1, "evidence-with-artifacts");
    expect(onSelectEvidence).toHaveBeenNthCalledWith(2, "trace-evidence");
  });

  it("highlights ablation diagnosis fields", async () => {
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
          artifact_ids: ["ablation:delta"],
          hypothesis: "检查 cross_modal_compare 是否暴露跨模态对齐或融合问题。",
          observation: "modality_ablation_check/cross_modal_compare judge_score=0，delta=conflict_actual_mismatch。",
          conclusion: "cross_modal_compare 失败，当前证据支持继续定位该变体覆盖的能力链路。",
          next_probe: "围绕 multimodal:conflict:1 执行 targeted evidence replay。"
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
      debug_strategy: [
        {
          stage: "ablation_expansion",
          objective: "验证跨模态失败是否稳定复现，且不是单模态感知失败。",
          trigger: "trace_refs=modality_ablation_check:cross_modal_compare",
          planned_probe: "对比 image/text 单模态结果与 cross_modal_compare 结果。",
          stop_condition: "单模态通过且 cross-modal probe 失败时，确认跨模态对齐/融合链路为主因。",
          escalation: "如果单模态也失败，切换到 single_modality_capability_gap 策略。"
        }
      ],
      follow_up_experiments: [
        {
          source: "debug_strategy",
          stage: "ablation_expansion",
          planned_steps: "strategy_ablation_expansion_probe",
          summary: "策略阶段 ablation_expansion 已转为 follow-up experiment：strategy_ablation_expansion_probe。"
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

    const onCreateStrategyFollowUp = vi.fn();

    render(<ReportPanel report={report} onCreateStrategyFollowUp={onCreateStrategyFollowUp} />);

    expect(screen.getByText("消融诊断")).toBeInTheDocument();
    const diagnosis = within(screen.getByLabelText("消融诊断"));
    expect(
      diagnosis.getByText("单模态变体 image_only, text_only 可通过，但跨模态变体 cross_modal_compare 失败。")
    ).toBeInTheDocument();
    expect(screen.getByText("根因追踪")).toBeInTheDocument();
    expect(screen.getByLabelText("根因追踪")).toHaveClass("evidence-spine");
    expect(screen.getByText("变体：cross_modal_compare")).toBeInTheDocument();
    expect(screen.getByText("模态：image, text")).toBeInTheDocument();
    expect(screen.getByText("证据：e-cross-modal")).toBeInTheDocument();
    expect(screen.getByText("缺失/偏差：conflict_actual_mismatch")).toBeInTheDocument();
    expect(screen.getByText("目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("产物：ablation:delta")).toBeInTheDocument();
    expect(screen.getByText("假设：检查 cross_modal_compare 是否暴露跨模态对齐或融合问题。")).toBeInTheDocument();
    expect(
      screen.getByText("观察：modality_ablation_check/cross_modal_compare judge_score=0，delta=conflict_actual_mismatch。")
    ).toBeInTheDocument();
    expect(screen.getByText("结论：cross_modal_compare 失败，当前证据支持继续定位该变体覆盖的能力链路。")).toBeInTheDocument();
    expect(screen.getByText("下一步：围绕 multimodal:conflict:1 执行 targeted evidence replay。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "建议操作" })).toBeInTheDocument();
    expect(screen.getByText("prompt/high：强化跨模态对比步骤。")).toBeInTheDocument();
    expect(screen.getAllByText("状态：待处理")[0]).toBeInTheDocument();
    expect(screen.getByText("要求模型先分别列出 image/text 证据，再输出冲突结论。")).toBeInTheDocument();
    expect(screen.getByText("model_capability/high：将跨模态融合短板纳入模型能力归因。")).toBeInTheDocument();
    expect(screen.getByLabelText("建议操作")).toHaveClass("action-console");
    expect(screen.getByText("调试策略")).toBeInTheDocument();
    expect(screen.getByLabelText("调试策略")).toHaveClass("evidence-spine");
    expect(screen.getByText("ablation_expansion：验证跨模态失败是否稳定复现，且不是单模态感知失败。")).toBeInTheDocument();
    expect(screen.getByText("触发：trace_refs=modality_ablation_check:cross_modal_compare")).toBeInTheDocument();
    expect(screen.getByText("探测：对比 image/text 单模态结果与 cross_modal_compare 结果。")).toBeInTheDocument();
    expect(screen.getByText("停止条件：单模态通过且 cross-modal probe 失败时，确认跨模态对齐/融合链路为主因。")).toBeInTheDocument();
    expect(screen.getByText("升级：如果单模态也失败，切换到 single_modality_capability_gap 策略。")).toBeInTheDocument();
    expect(screen.getByText("跟进实验")).toBeInTheDocument();
    expect(screen.getByLabelText("跟进实验")).toHaveClass("evidence-spine");
    expect(screen.getByText("debug_strategy/ablation_expansion：strategy_ablation_expansion_probe")).toBeInTheDocument();
    expect(screen.getByText("策略阶段 ablation_expansion 已转为 follow-up experiment：strategy_ablation_expansion_probe。")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "运行策略跟进 ablation_expansion" }));
    expect(onCreateStrategyFollowUp).toHaveBeenCalledWith("ablation_expansion");
    expect(screen.getByText("置信度理由")).toBeInTheDocument();
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

    await userEvent.click(screen.getByRole("button", { name: "接受建议操作 1" }));
    await userEvent.click(screen.getByRole("button", { name: "拒绝建议操作 1" }));
    await userEvent.click(screen.getByRole("button", { name: "标记建议操作 1 已应用" }));

    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(1, 0, "accepted");
    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(2, 0, "rejected");
    expect(onUpdateRecommendedActionStatus).toHaveBeenNthCalledWith(3, 0, "applied");
  });

  it("delegates strategy outcome escalation follow-up creation", async () => {
    const onCreateStrategyFollowUp = vi.fn();
    const report: DebugReport = {
      job_id: "job-strategy-outcome",
      case_id: "case-strategy-outcome",
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
      follow_up_experiments: [
        {
          source: "strategy_outcome",
          stage: "ablation_expansion",
          result: "needs_escalation",
          planned_steps: "strategy_escalation_single_modality_probe",
          summary:
            "策略阶段 ablation_expansion 的 follow-up job job-strategy-follow-up 未满足停止条件，已生成升级 probing：strategy_escalation_single_modality_probe。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(<ReportPanel report={report} onCreateStrategyFollowUp={onCreateStrategyFollowUp} />);

    expect(
      screen.getByText("strategy_outcome/ablation_expansion：strategy_escalation_single_modality_probe")
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "运行策略跟进 ablation_expansion" }));

    expect(onCreateStrategyFollowUp).toHaveBeenCalledWith("ablation_expansion");
  });

  it("delegates targeted probe follow-up creation", async () => {
    const onCreateTargetedProbe = vi.fn();
    const report: DebugReport = {
      job_id: "job-targeted",
      case_id: "case-targeted",
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
      follow_up_experiments: [
        {
          source: "targeted_probe",
          target_id: "multimodal:conflict:1",
          planned_steps: "targeted_multimodal_conflict_probe",
          summary: "围绕目标 multimodal:conflict:1 生成 targeted probing：targeted_multimodal_conflict_probe。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(<ReportPanel report={report} onCreateTargetedProbe={onCreateTargetedProbe} />);

    expect(screen.getByText("targeted_probe/unknown：targeted_multimodal_conflict_probe")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "运行定向深挖 multimodal:conflict:1" }));

    expect(onCreateTargetedProbe).toHaveBeenCalledWith("multimodal:conflict:1");
  });

  it("delegates targeted probe outcome escalation creation", async () => {
    const onCreateTargetedProbe = vi.fn();
    const report: DebugReport = {
      case_id: "case-targeted-outcome",
      job_id: "job-targeted-source",
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
        evidence_summary: "cross-modal target failed."
      },
      follow_up_experiments: [
        {
          source: "targeted_probe_outcome",
          target_id: "multimodal:conflict:1",
          result: "target_still_failing",
          planned_steps: "targeted_escalation_multimodal_conflict_probe",
          summary:
            "Targeted probe job job-targeted-probe for multimodal:conflict:1 未满足停止条件，已生成升级 probing：targeted_escalation_multimodal_conflict_probe。"
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(<ReportPanel report={report} onCreateTargetedProbe={onCreateTargetedProbe} />);

    expect(
      screen.getByText("targeted_probe_outcome/target_still_failing：targeted_escalation_multimodal_conflict_probe")
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "运行定向深挖 multimodal:conflict:1" }));

    expect(onCreateTargetedProbe).toHaveBeenCalledWith("multimodal:conflict:1");
  });

  it("renders targeted probe guardrail stop condition without runnable action", async () => {
    const onCreateTargetedProbe = vi.fn();
    const onCreateFinalAttributionFollowUp = vi.fn();
    const onCreateFinalAttributionRecovery = vi.fn();
    const onUpdateHumanHandoffStatus = vi.fn();
    const report: DebugReport = {
      case_id: "case-targeted-guardrail",
      job_id: "job-targeted-source",
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
        evidence_summary: "cross-modal target failed."
      },
      follow_up_experiments: [
        {
          source: "targeted_probe_guardrail",
          target_id: "multimodal:conflict:1",
          result: "target_still_failing",
          planned_steps: "",
          summary:
            "Targeted probe chain for multimodal:conflict:1 reached max depth 3; stop automatic escalation and require human review.",
          stop_condition: "max_targeted_probe_depth_reached"
        },
        {
          source: "final_attribution",
          target_id: "multimodal:conflict:1",
          category: "prompt_issue",
          planned_steps: "final_attribution_prompt_verification",
          summary:
            "Final attribution for multimodal:conflict:1 is prompt_issue; run final_attribution_prompt_verification to verify the recommended fix."
        },
        {
          source: "final_attribution_verification_outcome",
          target_id: "multimodal:conflict:1",
          category: "prompt_issue",
          result: "not_resolved",
          verification_job_id: "job-final-attribution-verify",
          planned_steps: "final_attribution_recovery_probe",
          summary:
            "Final attribution verification for multimodal:conflict:1 is not_resolved; run final_attribution_recovery_probe to reassess the root cause before closure."
        }
      ],
      human_handoff_requests: [
        {
          source: "targeted_probe_guardrail",
          target_id: "multimodal:conflict:1",
          priority: "high",
          reason: "max_targeted_probe_depth_reached",
          summary: "Targeted probe chain for multimodal:conflict:1 reached max depth 3.",
          recommended_owner: "human-debugger",
          next_action:
            "Review the full targeted probe chain, inspect evidence artifacts, and decide whether to update prompt, evaluation assets, or model capability attribution."
        }
      ],
      human_handoff_statuses: [
        {
          job_id: "job-targeted-source",
          target_id: "multimodal:conflict:1",
          status: "in_progress",
          actor: "human-debugger",
          note: "reviewing full probe chain",
          created_at: "2026-06-15T00:00:00+00:00",
          updated_at: "2026-06-15T00:00:01+00:00"
        }
      ],
      final_attributions: [
        {
          source: "human_handoff",
          target_id: "multimodal:conflict:1",
          category: "prompt_issue",
          status: "resolved",
          actor: "human-debugger",
          summary: "Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
          recommended_action: "Update prompt instructions and rerun verification before assigning model capability blame."
        }
      ],
      final_attribution_verification_results: [
        {
          source: "final_attribution",
          target_id: "multimodal:conflict:1",
          category: "prompt_issue",
          verification_job_id: "job-final-attribution-verify",
          result: "resolved",
          success_rate: 1,
          summary: "Final attribution verification for multimodal:conflict:1 resolved the issue."
        }
      ],
      final_attribution_recovery_results: [
        {
          source: "final_attribution_recovery",
          target_id: "multimodal:conflict:1",
          category: "prompt_issue",
          recovery_job_id: "job-final-attribution-recovery",
          result: "closed",
          success_rate: 1,
          summary: "Final attribution recovery for multimodal:conflict:1 closed the attribution loop."
        }
      ],
      suggested_sheet_fields: {
        错误原因: "跨模态对齐问题"
      }
    };

    render(
      <ReportPanel
        report={report}
        onCreateTargetedProbe={onCreateTargetedProbe}
        onCreateFinalAttributionFollowUp={onCreateFinalAttributionFollowUp}
        onCreateFinalAttributionRecovery={onCreateFinalAttributionRecovery}
        onUpdateHumanHandoffStatus={onUpdateHumanHandoffStatus}
      />
    );

    expect(screen.getByText("targeted_probe_guardrail/target_still_failing：")).toBeInTheDocument();
    expect(screen.getByText("停止条件：max_targeted_probe_depth_reached")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "人工接管请求" })).toBeInTheDocument();
    expect(screen.getByLabelText("人工接管请求")).toHaveClass("action-console");
    expect(screen.getByText("接管目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("接管优先级：high")).toBeInTheDocument();
    expect(screen.getByText("接管理由：max_targeted_probe_depth_reached")).toBeInTheDocument();
    expect(screen.getByText("接管状态：进行中")).toBeInTheDocument();
    expect(screen.getByText("接管处理人：human-debugger")).toBeInTheDocument();
    expect(screen.getByText("接管备注：reviewing full probe chain")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "最终归因" })).toBeInTheDocument();
    expect(screen.getByLabelText("最终归因")).toHaveClass("evidence-spine");
    expect(screen.getByText("归因目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("归因类别：prompt_issue")).toBeInTheDocument();
    expect(screen.getByText("归因状态：已解决")).toBeInTheDocument();
    expect(screen.getByText("归因操作者：human-debugger")).toBeInTheDocument();
    expect(
      screen.getByText(
        "归因建议：Update prompt instructions and rerun verification before assigning model capability blame."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "最终归因验证结果" })).toBeInTheDocument();
    expect(screen.getByText("归因验证目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("归因验证结果：已解决")).toBeInTheDocument();
    expect(screen.getByText("归因验证任务：job-final-attribution-verify")).toBeInTheDocument();
    expect(screen.getByText("归因验证通过率：100%")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "最终归因恢复结果" })).toBeInTheDocument();
    expect(screen.getByLabelText("最终归因恢复结果")).toHaveClass("evidence-spine");
    expect(screen.getByText("归因恢复目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(screen.getByText("归因恢复结果：已关闭")).toBeInTheDocument();
    expect(screen.getByText("归因恢复任务：job-final-attribution-recovery")).toBeInTheDocument();
    expect(screen.getByText("归因恢复通过率：100%")).toBeInTheDocument();
    expect(screen.getByText("建议负责人：human-debugger")).toBeInTheDocument();
    expect(
      screen.getByText(
        "下一步动作：Review the full targeted probe chain, inspect evidence artifacts, and decide whether to update prompt, evaluation assets, or model capability attribution."
      )
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "运行定向深挖 multimodal:conflict:1" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "运行最终归因跟进 multimodal:conflict:1" }));
    expect(onCreateFinalAttributionFollowUp).toHaveBeenCalledWith("multimodal:conflict:1");
    await userEvent.click(screen.getByRole("button", { name: "运行最终归因恢复 multimodal:conflict:1" }));
    expect(onCreateFinalAttributionRecovery).toHaveBeenCalledWith("multimodal:conflict:1");

    await userEvent.click(screen.getByRole("button", { name: "完成接管 multimodal:conflict:1" }));

    expect(onUpdateHumanHandoffStatus).toHaveBeenCalledWith("multimodal:conflict:1", "resolved");
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

    await userEvent.click(screen.getByRole("button", { name: "验证建议操作 1" }));

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

    expect(screen.getByText("建议操作状态事件")).toBeInTheDocument();
    expect(screen.getByText("操作 1：已接受")).toBeInTheDocument();
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

    expect(screen.getByText("建议操作验证任务")).toBeInTheDocument();
    expect(screen.getByText("操作 1 验证任务：job-verify-1")).toBeInTheDocument();
    expect(screen.getByText("操作者：qa-reviewer")).toBeInTheDocument();
    expect(screen.getByText("备注：verify prompt fix")).toBeInTheDocument();
    expect(screen.getByText("验证结果：已解决")).toBeInTheDocument();
    expect(screen.getByText("验证通过率：100%｜原通过率：50%")).toBeInTheDocument();
    expect(screen.getByText("验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。")).toBeInTheDocument();
  });

  it("renders auto debug closure lineage and trigger", async () => {
    const user = userEvent.setup();
    const onRunAutoDebugClosure = vi.fn();
    const report: DebugReport = {
      job_id: "job-auto-closure",
      case_id: "case-auto-closure",
      status: "needs_human_review",
      observed_failure: {
        type: "video_timestamp_mismatch",
        summary: "timestamp failed",
        affected_box_ids: []
      },
      planned_experiments: ["baseline_replay"],
      experiment_summary: null,
      root_cause: {
        label: "video_timestamp_boundary_error",
        confidence: "high",
        evidence_summary: "视频时间边界定位失败。"
      },
      suggested_sheet_fields: {
        错误原因: "视频时间边界定位失败"
      }
    };

    render(
      <ReportPanel
        report={report}
        onRunAutoDebugClosure={onRunAutoDebugClosure}
        autoDebugClosureResult={{
          source_job_id: "job-auto-closure",
          created_targeted_probe_jobs: ["job-probe-1"],
          created_strategy_follow_up_jobs: ["job-stability-1"],
          created_verification_jobs: ["job-verify-1"],
          final_attribution_candidates: [
            {
              category: "model_instability",
              confidence: "high",
              summary: "Live rerun passed 4/5 trials."
            }
          ],
          badcase_live_comparison: {
            original_badcase: "原 badcase：0/1 通过，avg_score=0.0。",
            live_rerun: "Live 复测：4/5 通过，success_rate=80%。",
            decision: "model_instability"
          },
          evidence_summaries: [
            {
              job_id: "job-auto-closure",
              evidence_id: "job-auto-closure:baseline_replay:0",
              step_name: "baseline_replay",
              trial: "0",
              judge_score: "0",
              delta_reasons: ["timestamp_end_out_of_range"],
              raw_output_excerpt: "{\"video_action_segments\":[{\"start_s\":0.0,\"end_s\":34.0}]}",
              model_call_error: "",
              response_parse_error: ""
            }
          ],
          targeted_probe_outcomes: [
            {
              probe_job_id: "job-probe-1",
              target_id: "video:segment:1",
              outcome: "corrected_boundary",
              summary: "Clipped targeted probe cleared video:segment:1."
            }
          ],
          writeback_status: "succeeded"
        }}
        autoDebugClosureMarkdown={
          "# case-auto-closure 最终 Debug 报告\n\n## 证据明细\n\n| 任务 | 证据 | 阶段 | 轮次 | 得分 | 缺失/偏差 | 模型原始输出摘录 |\n"
        }
        autoDebugClosureReportUrl="/api/artifacts/files/case-auto-closure-report.md"
      />
    );

    await user.click(screen.getByRole("button", { name: "运行自动闭环调试" }));

    expect(onRunAutoDebugClosure).toHaveBeenCalledTimes(1);
    expect(screen.getByText("自动定向深挖任务：job-probe-1")).toBeInTheDocument();
    expect(screen.getByText("自动稳定性跟进任务：job-stability-1")).toBeInTheDocument();
    expect(screen.getByText("自动闭环验证任务：job-verify-1")).toBeInTheDocument();
    expect(screen.getByText("原始 badcase：原 badcase：0/1 通过，avg_score=0.0。")).toBeInTheDocument();
    expect(screen.getByText("Live 复测对比：Live 复测：4/5 通过，success_rate=80%。")).toBeInTheDocument();
    expect(screen.getByText("闭环判断：model_instability")).toBeInTheDocument();
    expect(screen.getByText("model_instability/high：Live rerun passed 4/5 trials.")).toBeInTheDocument();
    expect(screen.getByText("自动闭环证据摘要")).toBeInTheDocument();
    expect(screen.getByText("定向深挖结果")).toBeInTheDocument();
    expect(screen.getByText("video:segment:1/corrected_boundary：Clipped targeted probe cleared video:segment:1.")).toBeInTheDocument();
    expect(screen.getByText("证据 job-auto-closure:baseline_replay:0 / baseline_replay / 得分=0")).toBeInTheDocument();
    expect(screen.getByText("缺失/偏差：timestamp_end_out_of_range")).toBeInTheDocument();
    expect(screen.getByText("原始输出：{\"video_action_segments\":[{\"start_s\":0.0,\"end_s\":34.0}]}")).toBeInTheDocument();
    expect(screen.getByText("自动闭环 Markdown 报告")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开自动闭环 Markdown 报告" })).toHaveAttribute(
      "href",
      "/api/artifacts/files/case-auto-closure-report.md"
    );
    expect(screen.getByText(/# case-auto-closure 最终 Debug 报告/)).toBeInTheDocument();
    expect(screen.getByText(/## 证据明细/)).toBeInTheDocument();
  });
});

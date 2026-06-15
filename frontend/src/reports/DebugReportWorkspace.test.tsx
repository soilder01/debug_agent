import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  DebugReport,
  ExperimentEvidence,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackResult,
  StrategyFollowUpJob,
  TargetedProbeJob
} from "../api/client";
import { DebugReportWorkspace } from "./DebugReportWorkspace";

function makeReport(overrides: Partial<DebugReport> = {}): DebugReport {
  return {
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
      evidence_ids: ["evidence-1"],
      image_artifact_ids: ["artifact-1"]
    },
    root_cause: {
      label: "unstable_handwriting_recognition",
      confidence: "medium",
      evidence_summary: "五次复测中存在波动。"
    },
    suggested_sheet_fields: {
      错误原因: "模型不稳定"
    },
    ...overrides
  };
}

function makeEvidence(): ExperimentEvidence {
  return {
    evidence_id: "evidence-1",
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
    raw_output: "{\"answers\":[]}",
    judge: {
      score: 0,
      reasons: ["box 7 mismatch"]
    },
    image_artifacts: []
  };
}

function makeWritebackResult(): SpreadsheetWritebackResult {
  return {
    row_id: "row-7",
    fields: {
      错误原因: "模型不稳定"
    }
  };
}

function makeWritebackAudit(): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "succeeded",
    row_id: "row-7",
    report_url: "https://debug-agent.local/report/job-1",
    fields: {},
    error_message: "",
    created_at: "2026-06-13T00:00:00+00:00",
    updated_at: "2026-06-13T00:00:01+00:00"
  };
}

function makeStrategyFollowUp(): StrategyFollowUpJob {
  return {
    source_job_id: "job-1",
    stage: "ablation_expansion",
    planned_steps: "strategy_ablation_expansion_probe",
    follow_up_job_id: "job-follow-up-1",
    actor: "strategy-operator",
    note: "run ablation expansion",
    created_at: "2026-06-15T00:00:02+00:00",
    outcome: "needs_escalation",
    success_rate: 0,
    summary: "Strategy follow-up job still failed; escalation is recommended.",
    escalation: "Run single-modality capability probes before keeping cross-modal attribution."
  };
}

function makeTargetedProbe(): TargetedProbeJob {
  return {
    source_job_id: "job-1",
    target_id: "multimodal:conflict:1",
    planned_steps: "targeted_multimodal_conflict_probe",
    probe_job_id: "job-targeted-probe-1",
    actor: "targeted-operator",
    note: "probe conflict target",
    created_at: "2026-06-15T00:00:02+00:00",
    outcome: "target_still_failing",
    success_rate: 0,
    summary: "Targeted probe still failed on multimodal:conflict:1; escalation is recommended.",
    escalation: "Run deeper localized replay or modality-specific probes for multimodal:conflict:1."
  };
}

describe("DebugReportWorkspace", () => {
  it("renders report workspace and delegates evidence and writeback actions", async () => {
    const onSelectEvidence = vi.fn();
    const onWriteReport = vi.fn();
    const onLoadWritebackAudit = vi.fn();

    render(
      <DebugReportWorkspace
        report={makeReport()}
        selectedEvidence={makeEvidence()}
        writebackResult={makeWritebackResult()}
        writebackAudit={makeWritebackAudit()}
        onSelectEvidence={onSelectEvidence}
        onWriteReport={onWriteReport}
        onLoadWritebackAudit={onLoadWritebackAudit}
      />
    );

    expect(screen.getByText("Job ID：job-1")).toBeInTheDocument();
    expect(screen.getByText("样本 ID：case-1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Experiment Plan" })).toBeInTheDocument();
    expect(screen.getByText("复测稳定性：unstable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spreadsheet Writeback" })).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet writeback row：row-7")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit status：succeeded")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "evidence-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Write report to spreadsheet" }));
    await userEvent.click(screen.getByRole("button", { name: "Load writeback audit" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("evidence-1");
    expect(onWriteReport).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudit).toHaveBeenCalledTimes(1);
  });

  it("hides spreadsheet writeback controls when the report has no job id", () => {
    render(
      <DebugReportWorkspace
        report={makeReport({ job_id: null })}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
      />
    );

    expect(screen.getByText("样本 ID：case-1")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Spreadsheet Writeback" })).not.toBeInTheDocument();
  });

  it("delegates evidence selection from report experiment trajectory", async () => {
    const onSelectEvidence = vi.fn();
    const report = makeReport({
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: [],
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
            evidence_ids: ["trajectory-evidence-1"],
            artifact_ids: ["ablation:delta"]
          }
        ]
      }
    });

    render(
      <DebugReportWorkspace
        report={report}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={onSelectEvidence}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "trajectory-evidence-1" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("trajectory-evidence-1");
  });

  it("delegates evidence selection from report artifact links", async () => {
    const onSelectEvidence = vi.fn();
    const report = makeReport({
      experiment_summary: {
        total_trials: 1,
        success_count: 0,
        failed_trial_count: 1,
        success_rate: 0,
        stability_label: "stable_failure",
        evidence_ids: ["artifact-evidence-1"],
        artifact_ids: ["artifact:video_segment_1:delta"],
        image_artifact_ids: [],
        step_summaries: [
          {
            step_name: "video_grounding",
            total_trials: 1,
            success_count: 0,
            failed_trial_count: 1,
            success_rate: 0,
            delta_reasons: ["segment_label_mismatch"],
            target_ids: ["video:segment:1"],
            evidence_ids: ["artifact-evidence-1"],
            artifact_ids: ["artifact:video_segment_1:delta"]
          }
        ]
      }
    });

    render(
      <DebugReportWorkspace
        report={report}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={onSelectEvidence}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Open artifact artifact:video_segment_1:delta" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("artifact-evidence-1");
  });

  it("delegates recommended action status updates from the report panel", async () => {
    const onUpdateRecommendedActionStatus = vi.fn();
    const report = makeReport({
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "pending",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ]
    });

    render(
      <DebugReportWorkspace
        report={report}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
        onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Accept recommended action 1" }));

    expect(onUpdateRecommendedActionStatus).toHaveBeenCalledWith(0, "accepted");
  });

  it("delegates recommended action verification reruns from the report panel", async () => {
    const onVerifyRecommendedAction = vi.fn();
    const report = makeReport({
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "applied",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
        }
      ]
    });

    render(
      <DebugReportWorkspace
        report={report}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
        onVerifyRecommendedAction={onVerifyRecommendedAction}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Verify recommended action 1" }));

    expect(onVerifyRecommendedAction).toHaveBeenCalledWith(0);
  });

  it("renders strategy follow-up job history and delegates opening follow-up jobs", async () => {
    const onOpenStrategyFollowUp = vi.fn();

    render(
      <DebugReportWorkspace
        report={makeReport()}
        selectedEvidence={null}
        strategyFollowUps={[makeStrategyFollowUp()]}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
        onOpenStrategyFollowUp={onOpenStrategyFollowUp}
      />
    );

    expect(screen.getByRole("heading", { name: "Strategy Follow-Up Job History" })).toBeInTheDocument();
    expect(screen.getByText("ablation_expansion：strategy_ablation_expansion_probe")).toBeInTheDocument();
    expect(screen.getByText("任务：job-follow-up-1")).toBeInTheDocument();
    expect(screen.getByText("Outcome：needs_escalation")).toBeInTheDocument();
    expect(screen.getByText("Success Rate：0%")).toBeInTheDocument();
    expect(screen.getByText("Strategy follow-up job still failed; escalation is recommended.")).toBeInTheDocument();
    expect(screen.getByText("Escalation：Run single-modality capability probes before keeping cross-modal attribution.")).toBeInTheDocument();
    expect(screen.getByText("操作者：strategy-operator")).toBeInTheDocument();
    expect(screen.getByText("备注：run ablation expansion")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open strategy follow-up job-follow-up-1" }));

    expect(onOpenStrategyFollowUp).toHaveBeenCalledWith("job-follow-up-1");
  });

  it("renders targeted probe job history and delegates opening probe jobs", async () => {
    const onOpenTargetedProbe = vi.fn();

    render(
      <DebugReportWorkspace
        report={makeReport()}
        selectedEvidence={null}
        targetedProbes={[makeTargetedProbe()]}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
        onOpenTargetedProbe={onOpenTargetedProbe}
      />
    );

    expect(screen.getByRole("heading", { name: "Targeted Probe Job History" })).toBeInTheDocument();
    expect(screen.getByText("multimodal:conflict:1：targeted_multimodal_conflict_probe")).toBeInTheDocument();
    expect(screen.getByText("任务：job-targeted-probe-1")).toBeInTheDocument();
    expect(screen.getByText("Outcome：target_still_failing")).toBeInTheDocument();
    expect(screen.getByText("Success Rate：0%")).toBeInTheDocument();
    expect(screen.getByText("Targeted probe still failed on multimodal:conflict:1; escalation is recommended.")).toBeInTheDocument();
    expect(screen.getByText("Escalation：Run deeper localized replay or modality-specific probes for multimodal:conflict:1.")).toBeInTheDocument();
    expect(screen.getByText("操作者：targeted-operator")).toBeInTheDocument();
    expect(screen.getByText("备注：probe conflict target")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open targeted probe job-targeted-probe-1" }));

    expect(onOpenTargetedProbe).toHaveBeenCalledWith("job-targeted-probe-1");
  });

  it("renders an explainability workspace narrative across evidence, diagnostics, confidence, actions, and verification", () => {
    const report = makeReport({
      root_cause_trace: [
        {
          step_name: "modality_ablation_check",
          variant: "cross_modal_compare",
          modalities: ["image", "text"],
          evidence_id: "trace-evidence",
          judge_score: 0,
          delta_reasons: ["conflict_actual_mismatch"],
          target_ids: ["multimodal:conflict:1"],
          artifact_ids: ["trace:delta"],
          hypothesis: "检查 cross_modal_compare 是否暴露跨模态对齐或融合问题。",
          observation: "cross_modal_compare judge_score=0。",
          conclusion: "cross_modal_compare 失败，支持跨模态归因。",
          next_probe: "围绕 multimodal:conflict:1 执行 targeted evidence replay。"
        }
      ],
      evaluation_asset_diagnostics: [
        {
          source: "scoring_standard",
          status: "fail",
          severity: "high",
          summary: "评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
          recommendation: "补充 exact match、可接受别字/格式、box_id 对齐等评分规则。",
          evidence_ids: "trace-evidence",
          artifact_ids: "trace:delta",
          trace_refs: "modality_ablation_check:cross_modal_compare"
        }
      ],
      confidence_reasons: [
        {
          source: "ablation_pattern",
          level: "high",
          summary: "root cause trace 包含 cross_modal_compare 变体，支持跨模态归因。",
          evidence_ids: "trace-evidence",
          artifact_ids: "trace:delta",
          trace_refs: "modality_ablation_check:cross_modal_compare"
        }
      ],
      recommended_actions: [
        {
          category: "prompt",
          priority: "high",
          status: "applied",
          summary: "强化跨模态对比步骤。",
          detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。",
          evidence_ids: "trace-evidence",
          artifact_ids: "trace:delta",
          trace_refs: "modality_ablation_check:cross_modal_compare"
        }
      ]
    });

    render(
      <DebugReportWorkspace
        report={report}
        selectedEvidence={null}
        recommendedActionVerifications={[
          {
            job_id: "job-1",
            action_index: 0,
            verification_job_id: "job-verify-1",
            actor: "local-dev-operator",
            note: "verify action",
            created_at: "2026-06-15T00:00:00+00:00"
          }
        ]}
        recommendedActionVerificationResults={[
          {
            job_id: "job-1",
            action_index: 0,
            verification_job_id: "job-verify-1",
            result: "resolved",
            source_success_rate: 0.4,
            verification_success_rate: 1,
            source_root_cause: "cross_modal_alignment_failure",
            verification_root_cause: "output_mismatch",
            summary: "验证任务通过率 100%，高于原任务 40%，推荐操作可能已修复该问题。"
          }
        ]}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "Explainability Workspace" })).toBeInTheDocument();
    expect(screen.getByText("Evidence spine：trace-evidence")).toBeInTheDocument();
    expect(screen.getByText("Diagnostic coverage：scoring_standard/fail/high")).toBeInTheDocument();
    expect(screen.getByText("Confidence coverage：ablation_pattern/high")).toBeInTheDocument();
    expect(screen.getByText("Action coverage：prompt/high/applied")).toBeInTheDocument();
    expect(screen.getByText("Verification coverage：job-verify-1/resolved")).toBeInTheDocument();
    expect(screen.getByText("Next probe：围绕 multimodal:conflict:1 执行 targeted evidence replay。")).toBeInTheDocument();
  });
});

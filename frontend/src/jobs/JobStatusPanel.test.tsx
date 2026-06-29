import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DebugJobStatus, DebugRunStage, EvidenceLedgerRecord } from "../api/client";
import { JobStatusPanel } from "./JobStatusPanel";

afterEach(() => {
  cleanup();
});

describe("JobStatusPanel", () => {
  it("renders formatted audit timestamps while preserving raw values", () => {
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "failed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 2,
      max_attempts: 2,
      remaining_attempts: 0,
      will_retry: false,
      retry_recommendation: "retry_budget_exhausted",
      retry_recommendation_detail: {
        code: "retry_budget_exhausted",
        label: "重试预算已耗尽",
        action: "不要继续自动重试，转人工检查任务错误和证据链。",
        severity: "critical"
      },
      error_message: "fixture failed",
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      },
      spreadsheet_writeback_audit: null
    } satisfies DebugJobStatus;

    render(<JobStatusPanel job={job} />);

    expect(screen.getByText("失败")).toHaveClass("status-badge--critical");
    expect(screen.getByText("严重")).toHaveClass("status-badge--critical");
    expect(screen.getByLabelText("任务尝试指标")).toHaveClass("metric-strip");
    expect(screen.getByText("创建时间：2026-06-11 10:00:01")).toHaveAttribute("title", "2026-06-11T10:00:01");
    expect(screen.getByText("更新时间：2026-06-11 10:00:02")).toHaveAttribute("title", "2026-06-11T10:00:02");
  });

  it("renders a persisted report loading action", async () => {
    const onLoadReport = vi.fn();
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "completed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 1,
      max_attempts: 2,
      remaining_attempts: 1,
      will_retry: false,
      retry_recommendation: "no_retry_needed",
      retry_recommendation_detail: {
        code: "no_retry_needed",
        label: "无需重试",
        action: "任务已完成，直接查看证据链和结论。",
        severity: "info"
      },
      error_message: null,
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      },
      spreadsheet_writeback_audit: null
    } satisfies DebugJobStatus;

    render(<JobStatusPanel job={job} onLoadReport={onLoadReport} />);
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));

    expect(onLoadReport).toHaveBeenCalledTimes(1);
  });

  it("renders spreadsheet writeback audit summary when present", () => {
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "completed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 1,
      max_attempts: 2,
      remaining_attempts: 1,
      will_retry: false,
      retry_recommendation: "no_retry_needed",
      retry_recommendation_detail: {
        code: "no_retry_needed",
        label: "无需重试",
        action: "任务已完成，直接查看证据链和结论。",
        severity: "info"
      },
      error_message: null,
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      },
      spreadsheet_writeback_audit: {
        status: "failed",
        row_id: "7",
        report_url: "https://debug-agent.local/jobs/job-detail-1/report",
        error_message: "permission denied",
        updated_at: "2026-06-12T06:00:01+00:00"
      }
    } satisfies DebugJobStatus;

    render(<JobStatusPanel job={job} />);

    expect(screen.getByText("写回状态：失败")).toBeInTheDocument();
    expect(screen.getByText("写回行：7")).toBeInTheDocument();
    expect(screen.getByText("写回错误：permission denied")).toBeInTheDocument();
  });

  it("renders debug run state machine stages", () => {
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "completed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 1,
      max_attempts: 2,
      remaining_attempts: 1,
      will_retry: false,
      retry_recommendation: "no_retry_needed",
      retry_recommendation_detail: {
        code: "no_retry_needed",
        label: "无需重试",
        action: "任务已完成，直接查看证据链和结论。",
        severity: "info"
      },
      error_message: null,
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      },
      spreadsheet_writeback_audit: null
    } satisfies DebugJobStatus;
    const runStages: DebugRunStage[] = [
      {
        job_id: "job-detail-1",
        stage: "baseline",
        status: "completed",
        input: { baseline_trials: 5 },
        output: { job_status: "completed" },
        failure_reason: "",
        retryable: false,
        attempt_count: 1,
        created_at: "2026-06-17T00:00:00+00:00",
        updated_at: "2026-06-17T00:00:01+00:00"
      },
      {
        job_id: "job-detail-1",
        stage: "writeback",
        status: "completed",
        input: { report_url: "/api/artifacts/files/report.md" },
        output: { writeback_status: "succeeded" },
        failure_reason: "",
        retryable: false,
        attempt_count: 1,
        created_at: "2026-06-17T00:00:02+00:00",
        updated_at: "2026-06-17T00:00:03+00:00"
      }
    ];

    render(<JobStatusPanel job={job} runStages={runStages} />);

    expect(screen.getByRole("region", { name: "Debug Run 状态机" })).toBeInTheDocument();
    expect(screen.getByText("baseline：已完成｜可重试：否")).toBeInTheDocument();
    expect(screen.getByText("writeback：已完成｜可重试：否")).toBeInTheDocument();
    expect(screen.getByText("输出：{\"writeback_status\":\"succeeded\"}")).toBeInTheDocument();
  });

  it("renders unified evidence ledger records", () => {
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "completed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 1,
      max_attempts: 2,
      remaining_attempts: 1,
      will_retry: false,
      retry_recommendation: "no_retry_needed",
      retry_recommendation_detail: {
        code: "no_retry_needed",
        label: "无需重试",
        action: "任务已完成，直接查看证据链和结论。",
        severity: "info"
      },
      error_message: null,
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      },
      spreadsheet_writeback_audit: null
    } satisfies DebugJobStatus;
    const evidenceLedger: EvidenceLedgerRecord[] = [
      {
        job_id: "job-detail-1",
        evidence_id: "job-detail-1:baseline:0",
        step_name: "baseline_replay",
        prompt: { prompt_length: 128 },
        enhanced_constraints: { target_id: "video:segment:1" },
        raw_output: "{\"video_action_segments\":[]}",
        parsed_result: { response_parse_error: "" },
        judge_version: "debug-agent-judge-v1",
        score_delta: { score: 0, reasons: ["timestamp_end_out_of_range"], deltas: [] },
        artifact_links: [{ artifact_id: "raw-output", uri: "/api/artifacts/files/raw.txt" }]
      }
    ];

    render(<JobStatusPanel job={job} evidenceLedger={evidenceLedger} />);

    expect(screen.getByRole("region", { name: "证据账本" })).toBeInTheDocument();
    expect(screen.getByText("账本证据：job-detail-1:baseline:0")).toBeInTheDocument();
    expect(screen.getByText("Prompt 摘要：{\"prompt_length\":128}")).toBeInTheDocument();
    expect(screen.getByText("增强约束：{\"target_id\":\"video:segment:1\"}")).toBeInTheDocument();
    expect(screen.getByText("Judge 版本：debug-agent-judge-v1")).toBeInTheDocument();
    expect(screen.getByText("Score delta：{\"score\":0,\"reasons\":[\"timestamp_end_out_of_range\"],\"deltas\":[]}")).toBeInTheDocument();
    expect(screen.getByText("产物：raw-output")).toBeInTheDocument();
  });
});

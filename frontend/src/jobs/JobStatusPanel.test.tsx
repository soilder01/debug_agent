import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DebugJobStatus } from "../api/client";
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

    expect(screen.getByText("failed")).toHaveClass("status-badge--critical");
    expect(screen.getByText("critical")).toHaveClass("status-badge--critical");
    expect(screen.getByLabelText("Job attempt metrics")).toHaveClass("metric-strip");
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
    await userEvent.click(screen.getByRole("button", { name: "Load persisted report" }));

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

    expect(screen.getByText("写回状态：failed")).toBeInTheDocument();
    expect(screen.getByText("写回行：7")).toBeInTheDocument();
    expect(screen.getByText("写回错误：permission denied")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { BatchDebugJobResponse, DebugJobStatus } from "../api/client";
import { BatchJobsPanel } from "./BatchJobsPanel";

function makeJob(overrides: Partial<DebugJobStatus> = {}): DebugJobStatus {
  return {
    job_id: "job-1",
    case_id: "case-1",
    status: "completed",
    created_at: "2026-06-12T10:00:01Z",
    updated_at: "2026-06-12T10:00:02Z",
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
    spreadsheet_writeback_audit: null,
    ...overrides
  };
}

function makeBatchResult(jobs: DebugJobStatus[]): BatchDebugJobResponse {
  return {
    jobs,
    rejected_case_ids: []
  };
}

describe("BatchJobsPanel", () => {
  it("renders controls and hides list before batch results are available", async () => {
    const onSubmit = vi.fn();
    const onLoadJobs = vi.fn();

    render(
      <BatchJobsPanel
        caseIds="case-1"
        batchResult={null}
        jobs={[]}
        summaryLabel="批量创建"
        totalCount={0}
        unloadedCount={0}
        completedCount={0}
        onCaseIdsChange={vi.fn()}
        onSubmit={onSubmit}
        onLoadJobs={onLoadJobs}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "调查工作台" })).toBeInTheDocument();
    expect(screen.getByText("这里执行已导入样本的 debug；还没有样本时，先去数据导入或回写同步。")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "调查工作台" })).toHaveClass("batch-jobs-panel");
    expect(screen.queryByLabelText("批量任务状态")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "批量提交调试" }));
    await userEvent.click(screen.getByRole("button", { name: "查看失败任务" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onLoadJobs).toHaveBeenCalledWith("failed", undefined);
  });

  it("renders batch job list when a batch result exists", () => {
    const jobs = [makeJob()];

    render(
      <BatchJobsPanel
        caseIds="case-1"
        batchResult={makeBatchResult(jobs)}
        jobs={jobs}
        summaryLabel="批量创建"
        totalCount={1}
        unloadedCount={0}
        completedCount={1}
        onCaseIdsChange={vi.fn()}
        onSubmit={vi.fn()}
        onLoadJobs={vi.fn()}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByLabelText("批量任务队列指标")).toBeInTheDocument();
    expect(screen.getByText("批量进度：1/1")).toBeInTheDocument();
    expect(screen.getByText("job-1：已完成")).toBeInTheDocument();
  });
});

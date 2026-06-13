import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugJobStatus } from "../api/client";
import { BatchJobListPanel } from "./BatchJobListPanel";

function makeJob(overrides: Partial<DebugJobStatus> = {}): DebugJobStatus {
  return {
    job_id: "job-batch-1",
    case_id: "case-1",
    status: "failed",
    created_at: "2026-06-12T10:00:01Z",
    updated_at: "2026-06-12T10:00:02Z",
    attempt_count: 1,
    max_attempts: 2,
    remaining_attempts: 1,
    will_retry: true,
    retry_recommendation: "retry_model_call_error",
    retry_recommendation_detail: {
      code: "retry_model_call_error",
      label: "模型调用错误，建议重试",
      action: "重新排队该任务。",
      severity: "warning"
    },
    error_message: "transient error",
    evidence_ids: ["ev-1"],
    evidence_error_counts: {
      total_evidence: 1,
      failed_judgements: 0,
      response_parse_errors: 0,
      model_call_errors: 1
    },
    spreadsheet_writeback_audit: null,
    ...overrides
  };
}

describe("BatchJobListPanel", () => {
  it("renders batch job summary and delegates row actions", async () => {
    const onStartWorker = vi.fn();
    const onLoadMore = vi.fn();
    const onOpenJob = vi.fn();
    const onSelectEvidence = vi.fn();
    const job = makeJob();

    render(
      <BatchJobListPanel
        jobs={[job]}
        summaryLabel="队列任务"
        totalCount={3}
        unloadedCount={2}
        rejectedCaseIds={["missing-case"]}
        completedCount={0}
        onStartWorker={onStartWorker}
        onLoadMore={onLoadMore}
        onOpenJob={onOpenJob}
        onSelectEvidence={onSelectEvidence}
      />
    );

    expect(screen.getByText("队列任务：1")).toBeInTheDocument();
    expect(screen.getByText("总任务：3")).toBeInTheDocument();
    expect(screen.getByText("未加载：2")).toBeInTheDocument();
    expect(screen.getByText("拒绝：missing-case")).toBeInTheDocument();
    expect(screen.getByText("批量进度：0/1")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1：failed")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 创建：2026-06-12 18:00:01")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 更新：2026-06-12 18:00:02")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 错误：transient error")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 建议：模型调用错误，建议重试")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 级别：warning")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Start worker for batch" }));
    await userEvent.click(screen.getByRole("button", { name: "Load more debug jobs" }));
    await userEvent.click(screen.getByRole("button", { name: "Open job job-batch-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Open evidence ev-1 for job job-batch-1" }));

    expect(onStartWorker).toHaveBeenCalledTimes(1);
    expect(onLoadMore).toHaveBeenCalledTimes(1);
    expect(onOpenJob).toHaveBeenCalledWith(job);
    expect(onSelectEvidence).toHaveBeenCalledWith("job-batch-1", "ev-1");
  });

  it("hides load more when all batch jobs are loaded", () => {
    render(
      <BatchJobListPanel
        jobs={[makeJob({ job_id: "job-loaded" })]}
        summaryLabel="队列任务"
        totalCount={1}
        unloadedCount={0}
        rejectedCaseIds={[]}
        completedCount={1}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByText("拒绝：无")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more debug jobs" })).not.toBeInTheDocument();
  });
});

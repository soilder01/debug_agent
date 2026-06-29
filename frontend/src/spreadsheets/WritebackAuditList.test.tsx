import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { WritebackAuditList } from "./WritebackAuditList";

function makeAudit(overrides: Partial<SpreadsheetWritebackAudit> = {}): SpreadsheetWritebackAudit {
  return {
    job_id: "job-failed-writeback-1",
    status: "failed",
    row_id: "7",
    report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
    fields: {},
    error_message: "permission denied",
    created_at: "2026-06-12T06:00:00+00:00",
    updated_at: "2026-06-12T06:00:01+00:00",
    ...overrides
  };
}

describe("WritebackAuditList", () => {
  it("renders audit list metadata and delegates row actions", async () => {
    const onOpenJob = vi.fn();
    const onRetry = vi.fn();
    const onLoadMore = vi.fn();

    render(
      <WritebackAuditList
        audits={[makeAudit()]}
        activeFilter="failed"
        totalCount={2}
        writebackResult={null}
        onOpenJob={onOpenJob}
        onRetry={onRetry}
        onLoadMore={onLoadMore}
      />
    );

    expect(screen.getByText("审计记录总数：2")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "回写审计列表" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("当前筛选：失败")).toBeInTheDocument();
    expect(screen.getByText("job-failed-writeback-1：失败｜行 7｜permission denied")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "打开任务 job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "重试写回 job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多审计记录" }));

    expect(onOpenJob).toHaveBeenCalledWith("job-failed-writeback-1");
    expect(onRetry).toHaveBeenCalledWith(makeAudit());
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("renders writeback retry result fields", () => {
    const writebackResult: SpreadsheetWritebackResult = {
      row_id: "7",
      fields: {
        错误原因: "model_weakness"
      }
    };

    render(
      <WritebackAuditList
        audits={[makeAudit()]}
        activeFilter={null}
        totalCount={1}
        writebackResult={writebackResult}
        onOpenJob={vi.fn()}
        onRetry={vi.fn()}
        onLoadMore={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：全部")).toBeInTheDocument();
    expect(screen.getByText("最近重试写回行：7")).toBeInTheDocument();
    expect(screen.getByText("错误原因：model_weakness")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "加载更多审计记录" })).not.toBeInTheDocument();
  });
});

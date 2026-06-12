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

    expect(screen.getByText("Writeback audits total：2")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit filter：failed")).toBeInTheDocument();
    expect(screen.getByText("job-failed-writeback-1：failed｜row 7｜permission denied")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open audit job job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Retry writeback job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Load more writeback audits" }));

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

    expect(screen.getByText("Writeback audit filter：all")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet writeback row：7")).toBeInTheDocument();
    expect(screen.getByText("错误原因：model_weakness")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more writeback audits" })).not.toBeInTheDocument();
  });
});

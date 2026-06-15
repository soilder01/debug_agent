import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetWritebackAuditCounts } from "../api/client";
import { WritebackAuditSummary } from "./WritebackAuditSummary";

describe("WritebackAuditSummary", () => {
  it("renders counts and delegates drilldown actions", async () => {
    const summary: SpreadsheetWritebackAuditCounts = {
      by_status: {
        succeeded: 8,
        failed: 2,
        skipped: 3
      },
      total_count: 13
    };
    const onLoadStatus = vi.fn();

    render(<WritebackAuditSummary summary={summary} onLoadStatus={onLoadStatus} />);

    expect(screen.getByLabelText("Writeback audit health metrics")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("Writeback audit filters")).toHaveClass("action-row");
    expect(screen.getByText("Writeback audit total：13")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit succeeded：8")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit failed：2")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit skipped：3")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "View succeeded writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "View failed writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "View skipped writeback audits" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, "succeeded");
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "failed");
    expect(onLoadStatus).toHaveBeenNthCalledWith(3, "skipped");
  });

  it("defaults missing status counts to zero", () => {
    render(<WritebackAuditSummary summary={{ by_status: {}, total_count: 0 }} onLoadStatus={vi.fn()} />);

    expect(screen.getByText("Writeback audit total：0")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit succeeded：0")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit failed：0")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit skipped：0")).toBeInTheDocument();
  });
});

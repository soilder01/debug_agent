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

    expect(screen.getByLabelText("回写审计健康指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("审计筛选")).toHaveClass("action-row");
    expect(screen.getByText("审计总数：13")).toBeInTheDocument();
    expect(screen.getByText("写回成功：8")).toBeInTheDocument();
    expect(screen.getByText("写回失败：2")).toBeInTheDocument();
    expect(screen.getByText("写回跳过：3")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "查看成功审计" }));
    await userEvent.click(screen.getByRole("button", { name: "查看失败审计" }));
    await userEvent.click(screen.getByRole("button", { name: "查看跳过审计" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, "succeeded");
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "failed");
    expect(onLoadStatus).toHaveBeenNthCalledWith(3, "skipped");
  });

  it("defaults missing status counts to zero", () => {
    render(<WritebackAuditSummary summary={{ by_status: {}, total_count: 0 }} onLoadStatus={vi.fn()} />);

    expect(screen.getByText("审计总数：0")).toBeInTheDocument();
    expect(screen.getByText("写回成功：0")).toBeInTheDocument();
    expect(screen.getByText("写回失败：0")).toBeInTheDocument();
    expect(screen.getByText("写回跳过：0")).toBeInTheDocument();
  });
});

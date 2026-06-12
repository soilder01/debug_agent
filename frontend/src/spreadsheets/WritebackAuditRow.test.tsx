import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetWritebackAudit } from "../api/client";
import { WritebackAuditRow } from "./WritebackAuditRow";

function makeAudit(overrides: Partial<SpreadsheetWritebackAudit> = {}): SpreadsheetWritebackAudit {
  return {
    job_id: "job-failed-writeback-1",
    status: "failed",
    row_id: "7",
    report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
    fields: {
      错误原因: "model_weakness"
    },
    error_message: "permission denied",
    created_at: "2026-06-12T06:00:00+00:00",
    updated_at: "2026-06-12T06:00:01+00:00",
    ...overrides
  };
}

describe("WritebackAuditRow", () => {
  it("renders failed audit details and supports retry", async () => {
    const onOpenJob = vi.fn();
    const onRetry = vi.fn();
    const audit = makeAudit();

    render(<WritebackAuditRow audit={audit} onOpenJob={onOpenJob} onRetry={onRetry} />);

    expect(screen.getByText("job-failed-writeback-1：failed｜row 7｜permission denied")).toBeInTheDocument();
    expect(screen.getByText("Retry eligibility：available")).toBeInTheDocument();
    expect(screen.getByText("Retry reason：last writeback failed")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit fields：1")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit field：错误原因=model_weakness")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open audit job job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Retry writeback job-failed-writeback-1" }));

    expect(onOpenJob).toHaveBeenCalledWith("job-failed-writeback-1");
    expect(onRetry).toHaveBeenCalledWith(audit);
  });

  it("hides retry for succeeded audits and keeps the report link", () => {
    const audit = makeAudit({
      job_id: "job-succeeded-writeback-1",
      status: "succeeded",
      row_id: "9",
      error_message: "",
      report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report"
    });

    render(<WritebackAuditRow audit={audit} onOpenJob={vi.fn()} onRetry={vi.fn()} />);

    expect(screen.getByText("job-succeeded-writeback-1：succeeded｜row 9｜无错误")).toBeInTheDocument();
    expect(screen.getByText("Retry eligibility：unavailable")).toBeInTheDocument();
    expect(screen.getByText("Retry reason：already succeeded")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry writeback job-succeeded-writeback-1" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open report job-succeeded-writeback-1" })).toHaveAttribute(
      "href",
      "https://debug-agent.local/jobs/job-succeeded-writeback-1/report"
    );
  });
});

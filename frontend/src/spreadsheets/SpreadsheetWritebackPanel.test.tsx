import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { SpreadsheetWritebackPanel } from "./SpreadsheetWritebackPanel";

function makeResult(overrides: Partial<SpreadsheetWritebackResult> = {}): SpreadsheetWritebackResult {
  return {
    row_id: "row-42",
    fields: {
      错误原因: "model_weakness",
      分析报告链接: "https://debug-agent.local/report"
    },
    ...overrides
  };
}

function makeAudit(overrides: Partial<SpreadsheetWritebackAudit> = {}): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "failed",
    row_id: "row-42",
    report_url: "https://debug-agent.local/report",
    fields: {},
    error_message: "permission denied",
    created_at: "2026-06-13T00:00:00+00:00",
    updated_at: "2026-06-13T00:00:01+00:00",
    ...overrides
  };
}

describe("SpreadsheetWritebackPanel", () => {
  it("renders writeback controls, result fields, and audit details", async () => {
    const onWriteReport = vi.fn();
    const onLoadAudit = vi.fn();

    render(
      <SpreadsheetWritebackPanel
        writebackResult={makeResult()}
        writebackAudit={makeAudit()}
        onWriteReport={onWriteReport}
        onLoadAudit={onLoadAudit}
      />
    );

    expect(screen.getByRole("heading", { name: "Spreadsheet Writeback" })).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet writeback row：row-42")).toBeInTheDocument();
    expect(screen.getByText("错误原因：model_weakness")).toBeInTheDocument();
    expect(screen.getByText("分析报告链接：https://debug-agent.local/report")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit status：failed")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit row：row-42")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit report URL：https://debug-agent.local/report")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit updated：2026-06-13T00:00:01+00:00")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Writeback audit error：permission denied");

    await userEvent.click(screen.getByRole("button", { name: "Write report to spreadsheet" }));
    await userEvent.click(screen.getByRole("button", { name: "Load writeback audit" }));

    expect(onWriteReport).toHaveBeenCalledTimes(1);
    expect(onLoadAudit).toHaveBeenCalledTimes(1);
  });

  it("hides optional result and audit details when absent", () => {
    render(
      <SpreadsheetWritebackPanel
        writebackResult={null}
        writebackAudit={null}
        onWriteReport={vi.fn()}
        onLoadAudit={vi.fn()}
      />
    );

    expect(screen.queryByText(/Spreadsheet writeback row/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Writeback audit status/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

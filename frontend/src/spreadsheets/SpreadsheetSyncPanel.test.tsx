import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  LarkSpreadsheetStatus,
  SpreadsheetSyncResponse,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackAuditCounts,
  SpreadsheetWritebackAuditListResponse,
  SpreadsheetWritebackResult
} from "../api/client";
import { SpreadsheetSyncPanel } from "./SpreadsheetSyncPanel";

function makeLarkStatus(): LarkSpreadsheetStatus {
  return {
    configured: true,
    spreadsheet_id: "spreadsheet-1",
    sheet_id: "sheet-1",
    lark_cli_timeout_seconds: 60,
    connectivity_status: "ok",
    error_message: ""
  };
}

function makeSyncResult(): SpreadsheetSyncResponse {
  return {
    imported_case_ids: ["case-1"],
    imported_rows: [{ sheet_row_id: "7", case_id: "case-1" }],
    jobs: [],
    rejected_rows: []
  };
}

function makeAudit(): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "failed",
    row_id: "7",
    report_url: "https://debug-agent.local/reports/job-1",
    fields: { 错误原因: "model_weakness" },
    error_message: "permission denied",
    created_at: "2026-06-12T06:00:00+00:00",
    updated_at: "2026-06-12T06:00:01+00:00"
  };
}

describe("SpreadsheetSyncPanel", () => {
  it("renders spreadsheet workspace sections and delegates actions", async () => {
    const audit = makeAudit();
    const summary: SpreadsheetWritebackAuditCounts = {
      by_status: { failed: 1, skipped: 2, succeeded: 3 },
      total_count: 6
    };
    const auditList: SpreadsheetWritebackAuditListResponse = {
      audits: [audit],
      total_count: 2
    };
    const writebackResult: SpreadsheetWritebackResult = {
      row_id: "7",
      fields: { 错误原因: "model_weakness" }
    };
    const onSyncSpreadsheet = vi.fn();
    const onLoadWritebackAudits = vi.fn();
    const onOpenAuditJob = vi.fn();
    const onRetryAudit = vi.fn();
    const onLoadMoreWritebackAudits = vi.fn();

    render(
      <SpreadsheetSyncPanel
        spreadsheetUrl="https://bytedance.larkoffice.com/sheets/spreadsheet-1?sheet=sheet-1"
        spreadsheetId="spreadsheet-1"
        sheetId="sheet-1"
        larkSpreadsheetStatus={makeLarkStatus()}
        syncResult={makeSyncResult()}
        writebackAuditSummary={summary}
        writebackAuditList={auditList}
        activeWritebackAuditStatus="failed"
        writebackResult={writebackResult}
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={onSyncSpreadsheet}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={onLoadWritebackAudits}
        onOpenAuditJob={onOpenAuditJob}
        onRetryAudit={onRetryAudit}
        onLoadMoreWritebackAudits={onLoadMoreWritebackAudits}
      />
    );

    expect(screen.getByRole("heading", { name: "Spreadsheet Sync" })).toBeInTheDocument();
    expect(screen.getByText("Lark 连接状态：ok")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 同步样本：1")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit total：6")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit filter：failed")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet writeback row：7")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sync spreadsheet rows" }));
    await userEvent.click(screen.getByRole("button", { name: "View failed writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "Open audit job job-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Retry writeback job-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Load more writeback audits" }));

    expect(onSyncSpreadsheet).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudits).toHaveBeenCalledWith("failed");
    expect(onOpenAuditJob).toHaveBeenCalledWith("job-1");
    expect(onRetryAudit).toHaveBeenCalledWith(audit);
    expect(onLoadMoreWritebackAudits).toHaveBeenCalledTimes(1);
  });

  it("hides optional result areas before data has loaded", () => {
    render(
      <SpreadsheetSyncPanel
        spreadsheetUrl=""
        spreadsheetId=""
        sheetId=""
        larkSpreadsheetStatus={null}
        syncResult={null}
        writebackAuditSummary={null}
        writebackAuditList={null}
        activeWritebackAuditStatus={null}
        writebackResult={null}
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={vi.fn()}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={vi.fn()}
        onOpenAuditJob={vi.fn()}
        onRetryAudit={vi.fn()}
        onLoadMoreWritebackAudits={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "Spreadsheet Sync" })).toBeInTheDocument();
    expect(screen.queryByText("Lark 连接状态：ok")).not.toBeInTheDocument();
    expect(screen.queryByText("Spreadsheet 同步样本：1")).not.toBeInTheDocument();
    expect(screen.queryByText("Writeback audit total：6")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Spreadsheet writeback audits")).not.toBeInTheDocument();
  });
});

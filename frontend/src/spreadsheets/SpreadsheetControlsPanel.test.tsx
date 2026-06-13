import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SpreadsheetControlsPanel } from "./SpreadsheetControlsPanel";

describe("SpreadsheetControlsPanel", () => {
  it("renders spreadsheet inputs and delegates value changes", async () => {
    const onSpreadsheetUrlChange = vi.fn();
    const onSpreadsheetIdChange = vi.fn();
    const onSheetIdChange = vi.fn();

    render(
      <SpreadsheetControlsPanel
        spreadsheetUrl="https://bytedance.larkoffice.com/sheets/sheet-token?sheet=grid-id"
        spreadsheetId="sheet-token"
        sheetId="grid-id"
        onSpreadsheetUrlChange={onSpreadsheetUrlChange}
        onSpreadsheetIdChange={onSpreadsheetIdChange}
        onSheetIdChange={onSheetIdChange}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={vi.fn()}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={vi.fn()}
      />
    );

    fireEvent.change(screen.getByLabelText("Lark spreadsheet URL"), {
      target: { value: "https://example.com/sheets/new?sheet=s1" }
    });
    fireEvent.change(screen.getByLabelText("Spreadsheet ID"), { target: { value: "new-spreadsheet" } });
    fireEvent.change(screen.getByLabelText("Sheet ID"), { target: { value: "new-sheet" } });

    expect(onSpreadsheetUrlChange).toHaveBeenLastCalledWith("https://example.com/sheets/new?sheet=s1");
    expect(onSpreadsheetIdChange).toHaveBeenLastCalledWith("new-spreadsheet");
    expect(onSheetIdChange).toHaveBeenLastCalledWith("new-sheet");
  });

  it("delegates spreadsheet sync and audit actions", async () => {
    const onUseSpreadsheetUrl = vi.fn();
    const onCheckLarkStatus = vi.fn();
    const onSyncSpreadsheet = vi.fn();
    const onLoadWritebackAuditSummary = vi.fn();
    const onLoadWritebackAudits = vi.fn();

    render(
      <SpreadsheetControlsPanel
        spreadsheetUrl=""
        spreadsheetId=""
        sheetId=""
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onUseSpreadsheetUrl={onUseSpreadsheetUrl}
        onCheckLarkStatus={onCheckLarkStatus}
        onSyncSpreadsheet={onSyncSpreadsheet}
        onLoadWritebackAuditSummary={onLoadWritebackAuditSummary}
        onLoadWritebackAudits={onLoadWritebackAudits}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Use spreadsheet URL" }));
    await userEvent.click(screen.getByRole("button", { name: "Check Lark status" }));
    await userEvent.click(screen.getByRole("button", { name: "Sync spreadsheet rows" }));
    await userEvent.click(screen.getByRole("button", { name: "Load writeback audit summary" }));
    await userEvent.click(screen.getByRole("button", { name: "Load all writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "Load succeeded writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "Load failed writeback audits" }));
    await userEvent.click(screen.getByRole("button", { name: "Load skipped writeback audits" }));

    expect(onUseSpreadsheetUrl).toHaveBeenCalledTimes(1);
    expect(onCheckLarkStatus).toHaveBeenCalledTimes(1);
    expect(onSyncSpreadsheet).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAuditSummary).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(1, null);
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(2, "succeeded");
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(3, "failed");
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(4, "skipped");
  });
});

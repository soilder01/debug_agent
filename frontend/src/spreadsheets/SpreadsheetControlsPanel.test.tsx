import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SpreadsheetControlsPanel } from "./SpreadsheetControlsPanel";

describe("SpreadsheetControlsPanel", () => {
  it("renders spreadsheet inputs and delegates value changes", async () => {
    const onSpreadsheetUrlChange = vi.fn();
    const onSpreadsheetIdChange = vi.fn();
    const onSheetIdChange = vi.fn();
    const onRerunRowIdsChange = vi.fn();
    const onRerunAutoClosureChange = vi.fn();
    const onRerunWritebackChange = vi.fn();

    render(
      <SpreadsheetControlsPanel
        spreadsheetUrl="https://example.larkoffice.com/sheets/sheet-token?sheet=grid-id"
        spreadsheetId="sheet-token"
        sheetId="grid-id"
        rerunRowIds="2-8"
        rerunAutoClosure={true}
        rerunWriteback={true}
        onSpreadsheetUrlChange={onSpreadsheetUrlChange}
        onSpreadsheetIdChange={onSpreadsheetIdChange}
        onSheetIdChange={onSheetIdChange}
        onRerunRowIdsChange={onRerunRowIdsChange}
        onRerunAutoClosureChange={onRerunAutoClosureChange}
        onRerunWritebackChange={onRerunWritebackChange}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={vi.fn()}
        onRerunSpreadsheetRows={vi.fn()}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={vi.fn()}
      />
    );

    expect(screen.getByRole("region", { name: "飞书链接控制台" })).toHaveClass("writeback-link-console");
    expect(screen.getByRole("region", { name: "重跑任务舱" })).toHaveClass("writeback-rerun-capsule");
    expect(screen.getByText("粘贴飞书表格链接")).toBeInTheDocument();
    expect(screen.getByText("解析链接")).toBeInTheDocument();
    expect(screen.getByText("检查连接")).toBeInTheDocument();
    expect(screen.getByText("同步表格")).toBeInTheDocument();
    expect(screen.getByText("重跑选中行")).toBeInTheDocument();
    expect(screen.getByText("自动闭环")).toBeInTheDocument();
    expect(screen.getByText("写回结果")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("飞书表格链接"), {
      target: { value: "https://example.com/sheets/new?sheet=s1" }
    });
    fireEvent.change(screen.getByLabelText("表格 Token"), { target: { value: "new-spreadsheet" } });
    fireEvent.change(screen.getByLabelText("工作表 ID"), { target: { value: "new-sheet" } });
    fireEvent.change(screen.getByLabelText("重跑行号"), { target: { value: "2,3" } });
    await userEvent.click(screen.getByRole("checkbox", { name: "启用自动闭环" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "写回重跑结果" }));

    expect(onSpreadsheetUrlChange).toHaveBeenLastCalledWith("https://example.com/sheets/new?sheet=s1");
    expect(onSpreadsheetIdChange).toHaveBeenLastCalledWith("new-spreadsheet");
    expect(onSheetIdChange).toHaveBeenLastCalledWith("new-sheet");
    expect(onRerunRowIdsChange).toHaveBeenLastCalledWith("2,3");
    expect(onRerunAutoClosureChange).toHaveBeenLastCalledWith(false);
    expect(onRerunWritebackChange).toHaveBeenLastCalledWith(false);
  });

  it("delegates spreadsheet sync and audit actions", async () => {
    const onUseSpreadsheetUrl = vi.fn();
    const onCheckLarkStatus = vi.fn();
    const onSyncSpreadsheet = vi.fn();
    const onRerunSpreadsheetRows = vi.fn();
    const onLoadWritebackAuditSummary = vi.fn();
    const onLoadWritebackAudits = vi.fn();

    render(
      <SpreadsheetControlsPanel
        spreadsheetUrl=""
        spreadsheetId=""
        sheetId=""
        rerunRowIds=""
        rerunAutoClosure={true}
        rerunWriteback={true}
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onRerunRowIdsChange={vi.fn()}
        onRerunAutoClosureChange={vi.fn()}
        onRerunWritebackChange={vi.fn()}
        onUseSpreadsheetUrl={onUseSpreadsheetUrl}
        onCheckLarkStatus={onCheckLarkStatus}
        onSyncSpreadsheet={onSyncSpreadsheet}
        onRerunSpreadsheetRows={onRerunSpreadsheetRows}
        onLoadWritebackAuditSummary={onLoadWritebackAuditSummary}
        onLoadWritebackAudits={onLoadWritebackAudits}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "解析飞书表格链接" }));
    await userEvent.click(screen.getByRole("button", { name: "检查飞书连接" }));
    await userEvent.click(screen.getByRole("button", { name: "同步表格行" }));
    await userEvent.click(screen.getByRole("button", { name: "重跑选中表格行" }));
    await userEvent.click(screen.getByRole("button", { name: "加载审计概览" }));
    await userEvent.click(screen.getByRole("button", { name: "加载全部审计" }));
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));
    await userEvent.click(screen.getByRole("button", { name: "加载跳过审计" }));

    expect(onUseSpreadsheetUrl).toHaveBeenCalledTimes(1);
    expect(onCheckLarkStatus).toHaveBeenCalledTimes(1);
    expect(onSyncSpreadsheet).toHaveBeenCalledTimes(1);
    expect(onRerunSpreadsheetRows).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAuditSummary).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(1, null);
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(2, "succeeded");
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(3, "failed");
    expect(onLoadWritebackAudits).toHaveBeenNthCalledWith(4, "skipped");
  });
});

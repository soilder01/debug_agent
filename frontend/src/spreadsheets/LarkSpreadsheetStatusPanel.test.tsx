import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LarkSpreadsheetStatus } from "../api/client";
import { LarkSpreadsheetStatusPanel } from "./LarkSpreadsheetStatusPanel";

function makeStatus(overrides: Partial<LarkSpreadsheetStatus> = {}): LarkSpreadsheetStatus {
  return {
    configured: true,
    connectivity_status: "ok",
    spreadsheet_id: "spreadsheet-123",
    sheet_id: "sheet-456",
    lark_cli_timeout_seconds: 60,
    error_message: "",
    ...overrides
  };
}

describe("LarkSpreadsheetStatusPanel", () => {
  it("renders configured Lark spreadsheet status details", () => {
    render(<LarkSpreadsheetStatusPanel status={makeStatus()} />);

    expect(screen.getByText("Lark 配置状态：已配置")).toBeInTheDocument();
    expect(screen.getByText("ok")).toHaveClass("status-badge--success");
    expect(screen.getByText("Lark 连接状态：ok")).toBeInTheDocument();
    expect(screen.getByText("Lark 表格：spreadsheet-123 / sheet-456")).toBeInTheDocument();
    expect(screen.getByText("Lark CLI 超时：60s")).toBeInTheDocument();
  });

  it("renders unconfigured status and optional error detail", () => {
    render(
      <LarkSpreadsheetStatusPanel
        status={makeStatus({
          configured: false,
          connectivity_status: "failed",
          spreadsheet_id: "",
          sheet_id: "",
          error_message: "permission denied"
        })}
      />
    );

    expect(screen.getByText("Lark 配置状态：未配置")).toBeInTheDocument();
    expect(screen.getByText("Lark 表格：无 / 无")).toBeInTheDocument();
    expect(screen.getByText("Lark 错误：permission denied")).toBeInTheDocument();
  });
});

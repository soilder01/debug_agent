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
    connector_mode: "cli",
    connector_identity: "bot",
    connector_profile: "debug-bot",
    connector_auth_status: "unknown",
    connector_token_status: "unknown",
    error_type: "",
    permission_scopes: [],
    console_url: "",
    risk_action: "",
    error_message: "",
    ...overrides
  };
}

describe("LarkSpreadsheetStatusPanel", () => {
  it("renders configured Lark spreadsheet status details", () => {
    render(<LarkSpreadsheetStatusPanel status={makeStatus()} />);

    expect(screen.getByText("Lark 配置状态：已配置")).toBeInTheDocument();
    expect(screen.getByText("正常")).toHaveClass("status-badge--success");
    expect(screen.getByText("Lark 连接状态：正常")).toBeInTheDocument();
    expect(screen.getByText("Lark 表格：spreadsheet-123 / sheet-456")).toBeInTheDocument();
    expect(screen.getByText("Lark CLI 超时：60s")).toBeInTheDocument();
    expect(screen.getByText("Lark Connector：cli / 身份 应用 / Profile debug-bot")).toBeInTheDocument();
    expect(screen.getByText("Lark 授权状态：unknown / Token unknown")).toBeInTheDocument();
  });

  it("renders unconfigured status and optional error detail", () => {
    render(
      <LarkSpreadsheetStatusPanel
        status={makeStatus({
          configured: false,
          connectivity_status: "failed",
          spreadsheet_id: "",
          sheet_id: "",
          error_type: "permission_denied",
          permission_scopes: ["sheets:spreadsheet:readonly"],
          console_url: "https://open.feishu.cn/app",
          error_message: "permission denied"
        })}
      />
    );

    expect(screen.getByText("Lark 配置状态：未配置")).toBeInTheDocument();
    expect(screen.getByText("Lark 表格：无 / 无")).toBeInTheDocument();
    expect(screen.getByText("Lark 错误类型：权限不足")).toBeInTheDocument();
    expect(screen.getByText("Lark 缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByText("Lark 权限配置入口：https://open.feishu.cn/app")).toBeInTheDocument();
    expect(screen.getByText("Lark 错误：permission denied")).toBeInTheDocument();
  });
});

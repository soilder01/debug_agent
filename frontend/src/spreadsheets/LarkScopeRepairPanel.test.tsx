import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LarkScopeCheckResponse } from "../api/client";
import { LarkScopeRepairPanel } from "./LarkScopeRepairPanel";

function makeScopeCheck(): LarkScopeCheckResponse {
  return {
    connector_mode: "cli",
    connector_identity: "bot",
    connector_profile: "debug-bot",
    auth_check_status: "not_verified",
    recent_missing_scopes: ["sheets:spreadsheet:readonly"],
    console_url: "https://open.larkoffice.com/app?lang=zh-CN",
    repair_steps: [
      "当前本地 CLI connector 不能直接读取租户已授权 scope，因此检查状态为 not_verified。",
      "在飞书开放平台打开当前应用的权限管理页面：https://open.larkoffice.com/app?lang=zh-CN",
      "确认应用至少具备这些 scope：sheets:spreadsheet:readonly。",
    ],
    requirements: [
      {
        service: "sheets",
        operation: "+csv-get",
        required_scopes: ["sheets:spreadsheet:readonly"],
        risk_level: "read",
        identity: "bot",
        confirmation_required: false,
        repair_hint: "在飞书开放平台为应用开通电子表格读取权限。",
        console_url: "https://open.larkoffice.com/app?lang=zh-CN",
        status: "missing_recently",
        recent_missing_scopes: ["sheets:spreadsheet:readonly"],
        recent_failure_count: 1
      }
    ]
  };
}

describe("LarkScopeRepairPanel", () => {
  it("renders Lark scope requirements and repair steps", () => {
    render(<LarkScopeRepairPanel scopeCheck={makeScopeCheck()} />);

    expect(screen.getByRole("region", { name: "Lark 权限修复建议" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("Lark 权限检查：未直接验证授权状态")).toBeInTheDocument();
    expect(screen.getByText("Connector：cli / 身份 应用 / Profile debug-bot")).toBeInTheDocument();
    expect(screen.getByText("最近缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByText("sheets +csv-get：最近失败审计显示缺失")).toBeInTheDocument();
    expect(screen.getByText("需要 scope：sheets:spreadsheet:readonly")).toBeInTheDocument();
    const repairSteps = screen.getByRole("list", { name: "Lark 权限修复步骤" });
    expect(within(repairSteps).getAllByRole("listitem")).toHaveLength(3);
  });
});

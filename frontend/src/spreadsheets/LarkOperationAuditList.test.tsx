import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkOperationAudit } from "../api/client";
import { LarkOperationAuditList } from "./LarkOperationAuditList";

function makeAudit(overrides: Partial<LarkOperationAudit> = {}): LarkOperationAudit {
  return {
    audit_id: 1,
    actor: "local-dev-operator",
    connector_mode: "cli",
    identity: "bot",
    profile: "debug-bot",
    service: "sheets",
    operation: "+csv-get",
    status: "failed",
    context: "+csv-get --spreadsheet-token sheet --sheet-id tab",
    error_type: "permission_denied",
    hint: "run lark-cli auth login",
    permission_scopes: ["sheets:spreadsheet:readonly"],
    console_url: "https://open.feishu.cn/app",
    risk_action: "",
    duration_ms: 12,
    created_at: "2026-06-22T00:00:00+00:00",
    ...overrides
  };
}

describe("LarkOperationAuditList", () => {
  it("renders operation audit details and delegates filters", async () => {
    const onLoadStatus = vi.fn();
    const onLoadMore = vi.fn();

    render(
      <LarkOperationAuditList
        audits={[makeAudit()]}
        totalCount={2}
        activeFilter="failed"
        onLoadStatus={onLoadStatus}
        onLoadMore={onLoadMore}
      />
    );

    expect(screen.getByRole("region", { name: "Lark 操作审计列表" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("Lark 操作审计总数：2")).toBeInTheDocument();
    expect(screen.getByText("当前筛选：失败")).toBeInTheDocument();
    expect(screen.getByText("sheets +csv-get：失败")).toBeInTheDocument();
    expect(screen.getByText("身份：应用 / Profile debug-bot / 耗时 12ms")).toBeInTheDocument();
    expect(screen.getByText("错误类型：权限不足")).toBeInTheDocument();
    expect(screen.getByText("缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByText("修复提示：run lark-cli auth login")).toBeInTheDocument();
    expect(screen.getByText("权限配置入口：https://open.feishu.cn/app")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "查看全部操作" }));
    await userEvent.click(screen.getByRole("button", { name: "查看成功操作" }));
    await userEvent.click(screen.getByRole("button", { name: "查看失败操作" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多 Lark 操作" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, null);
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "succeeded");
    expect(onLoadStatus).toHaveBeenNthCalledWith(3, "failed");
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("renders an empty state", () => {
    render(
      <LarkOperationAuditList
        audits={[]}
        totalCount={0}
        activeFilter={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：全部")).toBeInTheDocument();
    expect(screen.getByText("暂无 Lark 操作审计。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "加载更多 Lark 操作" })).not.toBeInTheDocument();
  });
});

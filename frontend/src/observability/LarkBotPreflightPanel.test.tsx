import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkBotPreflight } from "../api/client";
import { LarkBotPreflightPanel } from "./LarkBotPreflightPanel";

function makePreflight(): LarkBotPreflight {
  return {
    generated_at: "2026-06-23T00:00:00+00:00",
    status: "warning",
    connector: {
      mode: "cli",
      identity: "bot",
      profile: "xiaoD",
      auth_status: "unknown",
      token_status: "unknown"
    },
    event_mode: "long_connection",
    event_endpoint_url: "https://debug-agent.example/api/lark/bot/events",
    setup_package_url: "/api/lark/bot/setup-package.zip",
    required_bot_scopes: ["im:message.p2p_msg:readonly", "im:message:send_as_bot"],
    pending_command_count: 2,
    failed_command_count: 1,
    recent_missing_scopes: ["im:message:send_as_bot"],
    operator_required_items: [
      {
        key: "copy_encrypt_key",
        title: "同步 Encrypt Key",
        owner: "lark_app_admin",
        required: true,
        status: "done",
        detail: "configured=true",
        action: "无需处理。",
        evidence: "后端只记录是否已配置。",
        acknowledgement: {
          acknowledgement_id: 1,
          item_key: "copy_encrypt_key",
          actor: "ops",
          evidence: "审批单 FEISHU-123",
          note: "已确认",
          created_at: "2026-06-23T00:00:00+00:00"
        }
      },
      {
        key: "grant_im_bot_scope",
        title: "开通机器人 IM 发送权限",
        owner: "lark_app_admin",
        required: true,
        status: "needs_action",
        detail: "required=im:message:send_as_bot",
        action: "在飞书开放平台开通 im:message:send_as_bot。",
        evidence: "近期 Lark 操作审计记录了缺失权限。"
      }
    ],
    checks: [
      {
        key: "encrypt_key",
        label: "Encrypt Key",
        status: "passed",
        detail: "configured=true",
        action: "无需处理。"
      },
      {
        key: "im_scope_catalog",
        label: "IM 权限清单",
        status: "warning",
        detail: "required=im:message:send_as_bot",
        action: "在飞书开放平台开通 im:message:send_as_bot。"
      }
    ]
  };
}

describe("LarkBotPreflightPanel", () => {
  it("renders bot preflight checks and required scopes", () => {
    render(<LarkBotPreflightPanel preflight={makePreflight()} />);

    expect(screen.getByRole("heading", { name: "机器人上线预检" })).toBeInTheDocument();
    expect(screen.getByText("需关注")).toHaveClass("status-badge--warning");
    expect(screen.getByLabelText("机器人上线预检摘要")).toHaveClass("metric-strip");
    expect(screen.getByText("机器人预检状态：需关注")).toBeInTheDocument();
    expect(screen.getByText("机器人事件模式：长连接模式")).toBeInTheDocument();
    expect(screen.getByText("机器人预检身份：应用")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "下载接入交付包" })).toHaveAttribute(
      "href",
      "/api/lark/bot/setup-package.zip"
    );
    expect(screen.getByText("机器人接入交付包：/api/lark/bot/setup-package.zip")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "真实飞书接入清单" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("机器人接入事项：同步 Encrypt Key/已完成/飞书应用管理员")).toBeInTheDocument();
    expect(screen.getByText("机器人接入确认：同步 Encrypt Key/ops/审批单 FEISHU-123")).toBeInTheDocument();
    expect(screen.getByText(/最近确认：ops/)).toBeInTheDocument();
    expect(screen.getByText("机器人接入事项：开通机器人 IM 发送权限/需要处理/飞书应用管理员")).toBeInTheDocument();
    expect(screen.getByText("im:message.p2p_msg:readonly, im:message:send_as_bot")).toBeInTheDocument();
    expect(screen.getByText("近期缺失权限：im:message:send_as_bot")).toBeInTheDocument();
    expect(screen.getByText(/Encrypt Key：通过/)).toBeInTheDocument();
    expect(screen.getByText(/IM 权限清单：需关注/)).toBeInTheDocument();
  });

  it("submits setup acknowledgement records", async () => {
    const onAcknowledgeSetupItem = vi.fn().mockResolvedValue(undefined);
    render(<LarkBotPreflightPanel preflight={makePreflight()} onAcknowledgeSetupItem={onAcknowledgeSetupItem} />);

    await userEvent.selectOptions(screen.getByLabelText("确认事项"), "grant_im_bot_scope");
    await userEvent.clear(screen.getByLabelText("确认人"));
    await userEvent.type(screen.getByLabelText("确认人"), "lark-admin");
    await userEvent.type(screen.getByLabelText("证据"), "审批单 FEISHU-456");
    await userEvent.type(screen.getByLabelText("备注"), "权限已申请");
    await userEvent.click(screen.getByRole("button", { name: "记录确认" }));

    expect(onAcknowledgeSetupItem).toHaveBeenCalledWith("grant_im_bot_scope", {
      actor: "lark-admin",
      evidence: "审批单 FEISHU-456",
      note: "权限已申请"
    });
    expect(await screen.findByText("接入确认已记录")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LarkBotGoLiveGate } from "../api/client";
import { LarkBotGoLiveGatePanel } from "./LarkBotGoLiveGatePanel";

function makeGate(): LarkBotGoLiveGate {
  return {
    generated_at: "2026-06-23T00:00:00+00:00",
    status: "failed",
    allowed: false,
    decision: "暂不允许进入真实飞书机器人 dogfood。",
    preflight: {
      generated_at: "2026-06-23T00:00:00+00:00",
      status: "failed",
      connector: {
        mode: "cli",
        identity: "unknown",
        profile: "",
        auth_status: "unknown",
        token_status: "unknown"
      },
      event_mode: "long_connection",
      event_endpoint_url: "http://localhost:8000/api/lark/bot/events",
      setup_package_url: "/api/lark/bot/setup-package.zip",
      required_bot_scopes: ["im:message.p2p_msg:readonly", "im:message:send_as_bot"],
      pending_command_count: 1,
      failed_command_count: 0,
      recent_missing_scopes: [],
      operator_required_items: [],
      checks: []
    },
    checks: [
      {
        key: "manual_acknowledgements",
        label: "人工确认记录",
        status: "failed",
        detail: "缺少确认：运行 webhook 探针",
        action: "用记录确认表单补齐管理员确认和证据。"
      }
    ],
    export_urls: {
      permission_checklist: "/api/lark/bot/permission-checklist",
      setup_package: "/api/lark/bot/setup-package.zip",
      support_bundle: "/api/operations/support-bundle.zip"
    }
  };
}

describe("LarkBotGoLiveGatePanel", () => {
  it("renders go-live decision, checks, and export URLs", () => {
    render(<LarkBotGoLiveGatePanel gate={makeGate()} />);

    expect(screen.getByRole("heading", { name: "机器人真实上线门禁" })).toBeInTheDocument();
    expect(screen.getAllByText("阻塞")[0]).toHaveClass("status-badge--critical");
    expect(screen.getByLabelText("机器人上线门禁摘要")).toHaveClass("metric-strip");
    expect(screen.getByText("机器人真实上线门禁状态：阻塞")).toBeInTheDocument();
    expect(screen.getByText("机器人真实上线门禁结论：暂不允许")).toBeInTheDocument();
    expect(screen.getByText("机器人真实上线事件模式：长连接模式")).toBeInTheDocument();
    expect(screen.getByText(/人工确认记录：阻塞/)).toBeInTheDocument();
    expect(screen.getByText("机器人权限清单：/api/lark/bot/permission-checklist")).toBeInTheDocument();
    expect(screen.getByText("接入交付包：/api/lark/bot/setup-package.zip")).toBeInTheDocument();
  });
});

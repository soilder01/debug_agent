import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkBotPendingCommand, LarkBotReplyPayload } from "../api/client";
import { LarkBotPendingCommandPanel } from "./LarkBotPendingCommandPanel";

function makeCommand(overrides: Partial<LarkBotPendingCommand> = {}): LarkBotPendingCommand {
  return {
    command_id: "cmd-1",
    actor: "ops-reviewer",
    open_id: "ou_1",
    chat_id: "oc_1",
    message_id: "om_1",
    tenant_key: "tenant-1",
    identity: "bot",
    profile: "debug-bot",
    command_text: "/debug run case handwrite233",
    action_kind: "submit_case",
    action: {},
    card: {},
    status: "pending",
    note: "",
    execution_result: {},
    error_message: "",
    created_at: "2026-06-23T00:00:00+00:00",
    expires_at: "2026-06-23T01:00:00+00:00",
    confirmed_at: "",
    confirmed_by: "",
    executed_at: "",
    ...overrides
  };
}

const replyPreview: LarkBotReplyPayload = {
  command_id: "cmd-1",
  action_kind: "submit_case",
  status: "executed",
  target_type: "message",
  message_id: "om_1",
  chat_id: "oc_1",
  user_id: "ou_1",
  markdown: "## Debug Agent 已提交调试任务\n\n- 任务：`job-1`",
  idempotency_key: "debug-agent-bot-cmd-1-executed",
  delivery_args: ["im", "+messages-reply", "--message-id", "om_1", "--dry-run"]
};

describe("LarkBotPendingCommandPanel", () => {
  it("renders pending bot commands and delegates actions", async () => {
    const onLoadStatus = vi.fn();
    const onLoadMore = vi.fn();
    const onConfirm = vi.fn();
    const onPreviewReply = vi.fn();

    render(
      <LarkBotPendingCommandPanel
        commands={[makeCommand()]}
        totalCount={2}
        activeStatus="pending"
        replyPreview={replyPreview}
        onLoadStatus={onLoadStatus}
        onLoadMore={onLoadMore}
        onConfirm={onConfirm}
        onPreviewReply={onPreviewReply}
      />
    );

    expect(screen.getByRole("region", { name: "飞书机器人命令" })).toBeInTheDocument();
    expect(screen.getByText("机器人命令总数：2")).toBeInTheDocument();
    expect(screen.getByText("当前筛选：待确认")).toBeInTheDocument();
    expect(screen.getByText("/debug run case handwrite233")).toBeInTheDocument();
    expect(screen.getByText("待确认")).toBeInTheDocument();
    expect(screen.getByText(/操作者：ops-reviewer/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "机器人回复预览" })).toBeInTheDocument();
    expect(screen.getByText(/目标：原消息 om_1/)).toBeInTheDocument();
    expect(screen.getByText(/Debug Agent 已提交调试任务/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "查看全部机器人命令" }));
    await userEvent.click(screen.getByRole("button", { name: "查看已执行命令" }));
    await userEvent.click(screen.getByRole("button", { name: "确认并执行机器人命令" }));
    await userEvent.click(screen.getByRole("button", { name: "预览机器人回复" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多机器人命令" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, null);
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "executed");
    expect(onConfirm).toHaveBeenCalledWith("cmd-1");
    expect(onPreviewReply).toHaveBeenCalledWith("cmd-1");
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("renders empty state", () => {
    render(
      <LarkBotPendingCommandPanel
        commands={[]}
        totalCount={0}
        activeStatus={null}
        replyPreview={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
        onPreviewReply={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：全部")).toBeInTheDocument();
    expect(screen.getByText("暂无机器人命令")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "加载更多机器人命令" })).not.toBeInTheDocument();
  });
});

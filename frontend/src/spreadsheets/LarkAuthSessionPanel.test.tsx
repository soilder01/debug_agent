import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkAuthSession } from "../api/client";
import { LarkAuthSessionPanel } from "./LarkAuthSessionPanel";

function makeAuthSession(overrides: Partial<LarkAuthSession> = {}): LarkAuthSession {
  return {
    auth_session_id: "auth-1",
    actor: "local-dev-operator",
    identity: "user",
    profile: "debug-user",
    scopes: ["sheets:spreadsheet:readonly"],
    state: "state-1",
    auth_url: "https://open.larkoffice.com/app?debug_agent_auth=1",
    redirect_url: "",
    status: "pending",
    note: "need user auth",
    created_at: "2026-06-22T00:00:00+00:00",
    expires_at: "2026-06-22T00:30:00+00:00",
    completed_at: "",
    completed_by: "",
    ...overrides
  };
}

describe("LarkAuthSessionPanel", () => {
  it("renders pending auth session and delegates actions", async () => {
    const onCreateAuthSession = vi.fn();
    const onCompleteAuthSession = vi.fn();

    render(
      <LarkAuthSessionPanel
        authSession={makeAuthSession()}
        onCreateAuthSession={onCreateAuthSession}
        onCompleteAuthSession={onCompleteAuthSession}
      />
    );

    expect(screen.getByRole("region", { name: "Lark 授权会话" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("Lark 授权会话：待授权")).toBeInTheDocument();
    expect(screen.getByText("授权身份：用户 / Profile debug-user")).toBeInTheDocument();
    expect(screen.getByText("授权 scope：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开 Lark 授权入口" })).toHaveAttribute(
      "href",
      "https://open.larkoffice.com/app?debug_agent_auth=1"
    );

    await userEvent.click(screen.getByRole("button", { name: "创建 Lark 授权会话" }));
    await userEvent.click(screen.getByRole("button", { name: "标记 Lark 授权完成" }));

    expect(onCreateAuthSession).toHaveBeenCalledTimes(1);
    expect(onCompleteAuthSession).toHaveBeenCalledTimes(1);
  });

  it("disables completion before a session exists", () => {
    render(
      <LarkAuthSessionPanel
        authSession={null}
        onCreateAuthSession={vi.fn()}
        onCompleteAuthSession={vi.fn()}
      />
    );

    expect(screen.getByText("Lark 授权会话：未创建")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记 Lark 授权完成" })).toBeDisabled();
  });
});

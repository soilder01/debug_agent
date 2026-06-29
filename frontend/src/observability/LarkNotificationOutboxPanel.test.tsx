import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkNotificationOutbox } from "../api/client";
import { LarkNotificationOutboxPanel } from "./LarkNotificationOutboxPanel";

function makeNotification(overrides: Partial<LarkNotificationOutbox> = {}): LarkNotificationOutbox {
  return {
    notification_id: "badcase-completion:draft-1:job-1",
    kind: "badcase_completion",
    dedupe_key: "draft-1:job-1",
    status: "failed",
    draft_id: "draft-1",
    job_id: "job-1",
    case_id: "case-1",
    job_status: "completed",
    progress_key: "",
    payload: { delivery_args: ["im", "+messages-reply"] },
    envelope: { notification_id: "badcase-completion:draft-1:job-1" },
    attempts: 2,
    last_error: "invalid message id",
    created_at: "2026-06-26T00:00:00+00:00",
    updated_at: "2026-06-26T00:01:00+00:00",
    sent_at: "",
    ...overrides
  };
}

describe("LarkNotificationOutboxPanel", () => {
  it("renders notification outbox state and delegates filters", async () => {
    const onLoadStatus = vi.fn();
    const onLoadMore = vi.fn();

    render(
      <LarkNotificationOutboxPanel
        notifications={[makeNotification(), makeNotification({ notification_id: "progress-1", kind: "badcase_progress", status: "pending", attempts: 0, last_error: "" })]}
        totalCount={3}
        activeStatus="failed"
        onLoadStatus={onLoadStatus}
        onLoadMore={onLoadMore}
      />
    );

    expect(screen.getByRole("region", { name: "飞书通知 Outbox" })).toBeInTheDocument();
    expect(screen.getByText("通知总数：3")).toBeInTheDocument();
    expect(screen.getByText("当前筛选：失败")).toBeInTheDocument();
    expect(screen.getByText("badcase-completion:draft-1:job-1")).toBeInTheDocument();
    expect(screen.getAllByText("失败").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText((_, element) => element?.textContent?.includes("重试次数：2") ?? false)
        .length
    ).toBeGreaterThan(0);
    expect(screen.getByRole("alert")).toHaveTextContent("invalid message id");
    expect(screen.getAllByText(/任务：/).length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "查看待投递通知" }));
    await userEvent.click(screen.getByRole("button", { name: "查看已投递通知" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多通知" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, "pending");
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "sent");
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("renders empty state", () => {
    render(
      <LarkNotificationOutboxPanel
        notifications={[]}
        totalCount={0}
        activeStatus={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：全部")).toBeInTheDocument();
    expect(screen.getByText("暂无飞书通知")).toBeInTheDocument();
  });
});

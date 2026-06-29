import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FloatingAssistant } from "./FloatingAssistant";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("FloatingAssistant", () => {
  it("hides on the edge and opens a project assistant chat panel", async () => {
    render(<FloatingAssistant />);

    expect(screen.getByLabelText("项目助手")).toHaveAttribute("data-assistant-open", "false");
    await userEvent.click(screen.getByRole("button", { name: "唤醒项目助手" }));

    expect(screen.getByLabelText("项目助手")).toHaveAttribute("data-assistant-open", "true");
    expect(screen.getByRole("region", { name: "项目助手对话" })).toHaveClass("floating-assistant__panel");
    expect(screen.getByText("问我 Debug Agent 怎么用")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "关闭项目助手" }));
    expect(screen.getByLabelText("项目助手")).toHaveAttribute("data-assistant-open", "false");
    expect(screen.queryByRole("region", { name: "项目助手对话" })).not.toBeInTheDocument();
  });

  it("lets users drag the assistant without toggling the chat panel", () => {
    render(<FloatingAssistant />);

    const assistant = screen.getByLabelText("项目助手");
    const bot = screen.getByRole("button", { name: "唤醒项目助手" });
    fireEvent.mouseDown(bot, { clientX: 600, clientY: 500 });
    fireEvent.mouseMove(bot, { clientX: 520, clientY: 430 });
    fireEvent.mouseUp(bot, { clientX: 520, clientY: 430 });
    fireEvent.click(bot);

    expect(assistant).toHaveStyle({ right: "80px", bottom: "158px" });
    expect(assistant).toHaveAttribute("data-assistant-open", "false");
  });

  it("sends questions to the RAG assistant API and renders citations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          answer: "先去数据导入拿到 case_id，再到调查工作台批量提交调试。",
          citations: [{ title: "调查工作台", source: "workflow.md", snippet: "调查工作台执行已导入样本的 debug。" }],
          model_provider: "local-rag",
          model_id: "retrieval-only"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<FloatingAssistant />);
    await userEvent.click(screen.getByRole("button", { name: "唤醒项目助手" }));
    await userEvent.type(screen.getByLabelText("向项目助手提问"), "怎么提交调试任务？");
    await userEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/assistant/chat", {
      body: JSON.stringify({ question: "怎么提交调试任务？" }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("先去数据导入拿到 case_id，再到调查工作台批量提交调试。")).toBeInTheDocument();
    expect(screen.getByText("调查工作台｜workflow.md")).toBeInTheDocument();
    expect(screen.getByText("回答来源：local-rag")).toBeInTheDocument();
  });
});

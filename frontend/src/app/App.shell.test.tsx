import { App, describe, expect, it, openTab, render, screen, vi } from "./App.test.setup";

describe("App Shell", () => {
  it("renders the localized investigation workspace title", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "调查工作区" })).toBeInTheDocument();
    expect(screen.getByText("Harness Debug")).toBeInTheDocument();
    expect(screen.queryByText("Handwriting OCR Debug Agent")).not.toBeInTheDocument();
  });


  it("renders a productized debug console shell with motion hooks", () => {
    render(<App />);

    const shell = screen.getByRole("main");
    expect(shell).toHaveClass("app-main");
    expect(screen.getByText("Harness Debug").closest(".app-container")).toHaveAttribute("data-motion-scope", "debug-console");
    expect(screen.getByText("基于证据驱动的模型坏案排查与修复操作台")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "调查工作台" })).toHaveClass("batch-jobs-panel");
  });


  it("renders console navigation buttons for core work areas", () => {
    render(<App />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(navigation).toHaveClass("app-sidebar__nav");
    expect(screen.getByRole("button", { name: "调查工作区" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "数据导入" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "操作监控" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "回写同步" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "调查工作区" })).toBeInTheDocument();
  });


  it("keeps primary controls accessible when reduced motion is preferred", () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);

    render(<App />);

    expect(screen.getByText("Harness Debug").closest(".app-container")).toHaveAttribute("data-motion-scope", "debug-console");
    expect(screen.getByRole("button", { name: "提交调试任务" })).toBeVisible();
  });


  it("keeps critical operator controls reachable without hover-only affordances", async () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);

    render(<App />);

    expect(screen.getByRole("main")).toHaveClass("app-main");
    expect(screen.getByRole("navigation", { name: "主导航" })).toBeVisible();
    expect(screen.getByRole("button", { name: "提交调试任务" })).toBeVisible();

    await openTab("操作监控");
    expect(screen.getByRole("button", { name: "启动后台进程" })).toBeVisible();

    await openTab("数据导入");
    expect(screen.getByRole("button", { name: "加载导入样本" })).toBeVisible();

    await openTab("回写同步");
    expect(screen.getByRole("button", { name: "同步表格行" })).toBeVisible();

    await openTab("调查工作区");
    expect(screen.getByRole("region", { name: "调查工作台" })).toBeVisible();
  });
});

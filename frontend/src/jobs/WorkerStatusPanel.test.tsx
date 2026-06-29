import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WorkerStatus } from "../api/client";
import { WorkerStatusPanel } from "./WorkerStatusPanel";

function makeStatus(overrides: Partial<WorkerStatus> = {}): WorkerStatus {
  return {
    running: true,
    processed_count: 3,
    error_count: 1,
    recovered_stale_job_count: 2,
    last_error: "hook failed",
    completion_hook_enabled: true,
    report_base_url: "https://debug-agent.local",
    auto_writeback_enabled: false,
    ...overrides
  };
}

describe("WorkerStatusPanel", () => {
  it("renders worker counters and writeback settings", () => {
    render(<WorkerStatusPanel status={makeStatus()} />);

    expect(screen.getByText("进程运行中：是")).toBeInTheDocument();
    expect(screen.getByText("运行中")).toHaveClass("status-badge--success");
    expect(screen.getByLabelText("后台进程运行指标")).toHaveClass("metric-strip");
    expect(screen.getByText("已处理任务：3")).toBeInTheDocument();
    expect(screen.getByText("进程错误：1")).toBeInTheDocument();
    expect(screen.getByText("已恢复卡住任务：2")).toBeInTheDocument();
    expect(screen.getByText("自动回写配置：关闭")).toBeInTheDocument();
    expect(screen.getByText("完成回调：开启")).toBeInTheDocument();
    expect(screen.getByText("报告基础 URL：https://debug-agent.local")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("进程错误：hook failed");
  });

  it("hides worker error when there is no last error", () => {
    render(<WorkerStatusPanel status={makeStatus({ error_count: 0, last_error: null })} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

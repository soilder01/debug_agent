import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { WorkerStatus } from "../api/client";
import { WorkerControlsPanel } from "./WorkerControlsPanel";

function makeStatus(overrides: Partial<WorkerStatus> = {}): WorkerStatus {
  return {
    running: true,
    processed_count: 1,
    error_count: 0,
    last_error: null,
    completion_hook_enabled: true,
    report_base_url: "https://debug-agent.local",
    auto_writeback_enabled: true,
    ...overrides
  };
}

describe("WorkerControlsPanel", () => {
  it("renders worker controls and delegates actions", async () => {
    const onStart = vi.fn();
    const onStop = vi.fn();

    render(<WorkerControlsPanel status={makeStatus()} onStart={onStart} onStop={onStop} />);

    expect(screen.getByRole("heading", { name: "后台进程" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "后台进程" })).toHaveClass("worker-panel");
    expect(screen.getByLabelText("后台进程操作")).toHaveClass("action-row");
    expect(screen.getByText("进程运行中：是")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "启动后台进程" }));
    await userEvent.click(screen.getByRole("button", { name: "停止后台进程" }));

    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("hides worker status before it has loaded", () => {
    render(<WorkerControlsPanel status={null} onStart={vi.fn()} onStop={vi.fn()} />);

    expect(screen.queryByText(/进程运行中/)).not.toBeInTheDocument();
  });
});

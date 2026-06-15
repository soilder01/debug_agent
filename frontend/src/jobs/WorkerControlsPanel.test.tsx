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

    expect(screen.getByRole("heading", { name: "Worker" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Worker" })).toHaveClass("worker-panel");
    expect(screen.getByLabelText("Worker actions")).toHaveClass("action-row");
    expect(screen.getByText("Worker running：true")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Start worker" }));
    await userEvent.click(screen.getByRole("button", { name: "Stop worker" }));

    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("hides worker status before it has loaded", () => {
    render(<WorkerControlsPanel status={null} onStart={vi.fn()} onStop={vi.fn()} />);

    expect(screen.queryByText(/Worker running/)).not.toBeInTheDocument();
  });
});

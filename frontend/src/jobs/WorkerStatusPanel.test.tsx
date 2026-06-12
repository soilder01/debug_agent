import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WorkerStatus } from "../api/client";
import { WorkerStatusPanel } from "./WorkerStatusPanel";

function makeStatus(overrides: Partial<WorkerStatus> = {}): WorkerStatus {
  return {
    running: true,
    processed_count: 3,
    error_count: 1,
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

    expect(screen.getByText("Worker running：true")).toBeInTheDocument();
    expect(screen.getByText("Worker processed：3")).toBeInTheDocument();
    expect(screen.getByText("Worker errors：1")).toBeInTheDocument();
    expect(screen.getByText("Worker auto writeback setting：disabled")).toBeInTheDocument();
    expect(screen.getByText("Worker auto writeback：enabled")).toBeInTheDocument();
    expect(screen.getByText("Worker report base URL：https://debug-agent.local")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Worker error：hook failed");
  });

  it("hides worker error when there is no last error", () => {
    render(<WorkerStatusPanel status={makeStatus({ error_count: 0, last_error: null })} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

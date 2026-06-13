import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ObservabilitySummary } from "../api/client";
import { ObservabilitySummaryPanel } from "./ObservabilitySummaryPanel";

function makeSummary(): ObservabilitySummary {
  return {
    jobs: {
      by_status: {
        created: 4,
        running: 1,
        completed: 12,
        failed: 2
      },
      total_count: 19,
      pending_count: 4,
      running_count: 1,
      failed_count: 2,
      completed_count: 12
    },
    worker: {
      running: true,
      processed_count: 18,
      error_count: 1,
      last_error: "hook failed",
      completion_hook_enabled: true,
      report_base_url: "https://debug-agent.local",
      auto_writeback_enabled: true
    },
    writeback_audits: {
      by_status: {
        succeeded: 10,
        failed: 2,
        skipped: 1
      },
      total_count: 13
    },
    evidence: {
      total_evidence: 42,
      failed_judgements: 11,
      response_parse_errors: 3,
      model_call_errors: 2,
      average_latency_ms: 88.5
    },
    health: {
      level: "critical",
      reasons: ["failed jobs present", "failed spreadsheet writebacks present", "model call errors present"]
    }
  };
}

describe("ObservabilitySummaryPanel", () => {
  it("renders job, worker, and writeback operational metrics", () => {
    render(<ObservabilitySummaryPanel summary={makeSummary()} />);

    expect(screen.getByRole("heading", { name: "Observability" })).toBeInTheDocument();
    expect(screen.getByText("Observed jobs total：19")).toBeInTheDocument();
    expect(screen.getByText("Observed jobs pending：4")).toBeInTheDocument();
    expect(screen.getByText("Observed jobs running：1")).toBeInTheDocument();
    expect(screen.getByText("Observed jobs completed：12")).toBeInTheDocument();
    expect(screen.getByText("Observed jobs failed：2")).toBeInTheDocument();
    expect(screen.getByText("Observed worker running：true")).toBeInTheDocument();
    expect(screen.getByText("Observed worker processed：18")).toBeInTheDocument();
    expect(screen.getByText("Observed worker errors：1")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Observed worker last error：hook failed");
    expect(screen.getByText("Observed writeback audits total：13")).toBeInTheDocument();
    expect(screen.getByText("Observed writeback succeeded：10")).toBeInTheDocument();
    expect(screen.getByText("Observed writeback failed：2")).toBeInTheDocument();
    expect(screen.getByText("Observed writeback skipped：1")).toBeInTheDocument();
    expect(screen.getByText("Observed evidence total：42")).toBeInTheDocument();
    expect(screen.getByText("Observed evidence failed judgements：11")).toBeInTheDocument();
    expect(screen.getByText("Observed evidence parse errors：3")).toBeInTheDocument();
    expect(screen.getByText("Observed evidence model call errors：2")).toBeInTheDocument();
    expect(screen.getByText("Observed evidence avg latency：88.5ms")).toBeInTheDocument();
    expect(screen.getByText("Observed health：critical")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：failed jobs present")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：failed spreadsheet writebacks present")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：model call errors present")).toBeInTheDocument();
  });
});

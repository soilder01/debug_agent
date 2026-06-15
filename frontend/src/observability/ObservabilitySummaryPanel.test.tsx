import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
    usage: {
      model_call_count: 42,
      prompt_character_count: 12345,
      estimated_cost_units: 54.345,
      budget_units: 50,
      budget_status: "over_budget",
      budget_utilization: 1.0869,
      budget_enforcement_enabled: true
    },
    strategy_feedback: {
      total_follow_ups: 6,
      pending_count: 2,
      passed_stop_condition_count: 3,
      needs_escalation_count: 1
    },
    health: {
      level: "critical",
      reasons: [
        "failed jobs present",
        "failed spreadsheet writebacks present",
        "model call errors present",
        "strategy follow-ups need escalation"
      ],
      actions: [
        "Inspect failed jobs and open their evidence chain.",
        "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers.",
        "Check model endpoint health, timeout settings, and retry affected jobs.",
        "Open strategy follow-up history and run escalation probes."
      ]
    }
  };
}

describe("ObservabilitySummaryPanel", () => {
  it("renders job, worker, and writeback operational metrics", async () => {
    const onLoadFailedJobs = vi.fn();
    const onLoadFailedWritebacks = vi.fn();
    const onStartWorker = vi.fn();

    render(
      <ObservabilitySummaryPanel
        summary={makeSummary()}
        onLoadFailedJobs={onLoadFailedJobs}
        onLoadFailedWritebacks={onLoadFailedWritebacks}
        onStartWorker={onStartWorker}
      />
    );

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
    expect(screen.getByText("Observed model calls：42")).toBeInTheDocument();
    expect(screen.getByText("Observed prompt chars：12345")).toBeInTheDocument();
    expect(screen.getByText("Observed estimated cost units：54.345")).toBeInTheDocument();
    expect(screen.getByText("Observed usage budget：50")).toBeInTheDocument();
    expect(screen.getByText("Observed budget status：over_budget")).toBeInTheDocument();
    expect(screen.getByText("Observed budget utilization：1.0869")).toBeInTheDocument();
    expect(screen.getByText("Observed budget enforcement：enabled")).toBeInTheDocument();
    expect(screen.getByText("Observed strategy follow-ups：6")).toBeInTheDocument();
    expect(screen.getByText("Observed strategy pending：2")).toBeInTheDocument();
    expect(screen.getByText("Observed strategy passed stop condition：3")).toBeInTheDocument();
    expect(screen.getByText("Observed strategy needs escalation：1")).toBeInTheDocument();
    expect(screen.getByText("Observed health：critical")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：failed jobs present")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：failed spreadsheet writebacks present")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：model call errors present")).toBeInTheDocument();
    expect(screen.getByText("Observed health reason：strategy follow-ups need escalation")).toBeInTheDocument();
    expect(screen.getByText("Recommended action：Inspect failed jobs and open their evidence chain.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Recommended action：Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Recommended action：Check model endpoint health, timeout settings, and retry affected jobs.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Recommended action：Open strategy follow-up history and run escalation probes.")
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open failed jobs from observability" }));
    await userEvent.click(screen.getByRole("button", { name: "Open failed writebacks from observability" }));
    await userEvent.click(screen.getByRole("button", { name: "Start worker from observability" }));

    expect(onLoadFailedJobs).toHaveBeenCalledTimes(1);
    expect(onLoadFailedWritebacks).toHaveBeenCalledTimes(1);
    expect(onStartWorker).toHaveBeenCalledTimes(1);
  });
});

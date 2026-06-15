import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugJobStatus, ExperimentEvidence } from "../api/client";
import { CurrentJobPanel } from "./CurrentJobPanel";

function makeJob(): DebugJobStatus {
  return {
    job_id: "job-1",
    case_id: "case-1",
    status: "completed",
    created_at: "2026-06-11T10:00:01",
    updated_at: "2026-06-11T10:00:02",
    attempt_count: 1,
    max_attempts: 2,
    remaining_attempts: 1,
    will_retry: false,
    retry_recommendation: "no_retry_needed",
    retry_recommendation_detail: {
      code: "no_retry_needed",
      label: "无需重试",
      action: "任务已完成，直接查看证据链和结论。",
      severity: "info"
    },
    error_message: null,
    evidence_ids: ["evidence-1"],
    evidence_error_counts: {
      total_evidence: 1,
      failed_judgements: 0,
      response_parse_errors: 0,
      model_call_errors: 0
    },
    spreadsheet_writeback_audit: null
  };
}

function makeEvidence(): ExperimentEvidence {
  return {
    evidence_id: "evidence-1",
    step_name: "baseline_replay",
    trial: 0,
    model_name: "ark-seed2-lite",
    model_provider: "ark",
    model_id: "ep-seed2-lite",
    request_summary: {
      prompt_length: 42,
      has_image: true,
      image_uri_scheme: "file"
    },
    latency_ms: 25,
    response_parse_error: "",
    model_call_error_type: "",
    model_call_error_message: "",
    image_artifacts: [],
    raw_output: "{\"answers\":[]}",
    judge: {
      score: 0,
      reasons: ["box 7 mismatch"]
    }
  };
}

describe("CurrentJobPanel", () => {
  it("renders current job status, selected evidence, and delegates actions", async () => {
    const onSelectEvidence = vi.fn();
    const onLoadReport = vi.fn();

    render(
      <CurrentJobPanel
        job={makeJob()}
        selectedEvidence={makeEvidence()}
        onSelectEvidence={onSelectEvidence}
        onLoadReport={onLoadReport}
      />
    );

    expect(screen.getByRole("region", { name: "Current job workspace" })).toHaveClass("current-job-panel");
    expect(screen.getByRole("heading", { name: "Job Status" })).toBeInTheDocument();
    expect(screen.getByLabelText("Job status actions")).toHaveClass("action-row");
    expect(screen.getByText("Job ID：job-1")).toBeInTheDocument();
    expect(screen.getByText("证据数：1")).toBeInTheDocument();
    expect(screen.getByText("证据 ID：evidence-1")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "View evidence evidence-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Load persisted report" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("evidence-1");
    expect(onLoadReport).toHaveBeenCalledTimes(1);
  });

  it("renders without selected evidence", () => {
    render(
      <CurrentJobPanel
        job={makeJob()}
        selectedEvidence={null}
        onSelectEvidence={vi.fn()}
        onLoadReport={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "Job Status" })).toBeInTheDocument();
    expect(screen.queryByText("证据 ID：evidence-1")).not.toBeInTheDocument();
  });
});

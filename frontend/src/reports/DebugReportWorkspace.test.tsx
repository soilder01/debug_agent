import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugReport, ExperimentEvidence, SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { DebugReportWorkspace } from "./DebugReportWorkspace";

function makeReport(overrides: Partial<DebugReport> = {}): DebugReport {
  return {
    job_id: "job-1",
    case_id: "case-1",
    status: "needs_human_review",
    observed_failure: {
      type: "ocr_mismatch",
      summary: "box 7 mismatch",
      affected_box_ids: [7]
    },
    planned_experiments: ["baseline_replay"],
    experiment_summary: {
      total_trials: 5,
      success_count: 2,
      failed_trial_count: 3,
      success_rate: 0.4,
      stability_label: "unstable",
      evidence_ids: ["evidence-1"],
      image_artifact_ids: ["artifact-1"]
    },
    root_cause: {
      label: "unstable_handwriting_recognition",
      confidence: "medium",
      evidence_summary: "五次复测中存在波动。"
    },
    suggested_sheet_fields: {
      错误原因: "模型不稳定"
    },
    ...overrides
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
    raw_output: "{\"answers\":[]}",
    judge: {
      score: 0,
      reasons: ["box 7 mismatch"]
    },
    image_artifacts: []
  };
}

function makeWritebackResult(): SpreadsheetWritebackResult {
  return {
    row_id: "row-7",
    fields: {
      错误原因: "模型不稳定"
    }
  };
}

function makeWritebackAudit(): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "succeeded",
    row_id: "row-7",
    report_url: "https://debug-agent.local/report/job-1",
    fields: {},
    error_message: "",
    created_at: "2026-06-13T00:00:00+00:00",
    updated_at: "2026-06-13T00:00:01+00:00"
  };
}

describe("DebugReportWorkspace", () => {
  it("renders report workspace and delegates evidence and writeback actions", async () => {
    const onSelectEvidence = vi.fn();
    const onWriteReport = vi.fn();
    const onLoadWritebackAudit = vi.fn();

    render(
      <DebugReportWorkspace
        report={makeReport()}
        selectedEvidence={makeEvidence()}
        writebackResult={makeWritebackResult()}
        writebackAudit={makeWritebackAudit()}
        onSelectEvidence={onSelectEvidence}
        onWriteReport={onWriteReport}
        onLoadWritebackAudit={onLoadWritebackAudit}
      />
    );

    expect(screen.getByText("Job ID：job-1")).toBeInTheDocument();
    expect(screen.getByText("样本 ID：case-1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Experiment Plan" })).toBeInTheDocument();
    expect(screen.getByText("复测稳定性：unstable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spreadsheet Writeback" })).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet writeback row：row-7")).toBeInTheDocument();
    expect(screen.getByText("Writeback audit status：succeeded")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "evidence-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Write report to spreadsheet" }));
    await userEvent.click(screen.getByRole("button", { name: "Load writeback audit" }));

    expect(onSelectEvidence).toHaveBeenCalledWith("evidence-1");
    expect(onWriteReport).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudit).toHaveBeenCalledTimes(1);
  });

  it("hides spreadsheet writeback controls when the report has no job id", () => {
    render(
      <DebugReportWorkspace
        report={makeReport({ job_id: null })}
        selectedEvidence={null}
        writebackResult={null}
        writebackAudit={null}
        onSelectEvidence={vi.fn()}
        onWriteReport={vi.fn()}
        onLoadWritebackAudit={vi.fn()}
      />
    );

    expect(screen.getByText("样本 ID：case-1")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Spreadsheet Writeback" })).not.toBeInTheDocument();
  });
});

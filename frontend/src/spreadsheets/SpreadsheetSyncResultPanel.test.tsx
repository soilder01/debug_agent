import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SpreadsheetSyncResponse } from "../api/client";
import { SpreadsheetSyncResultPanel } from "./SpreadsheetSyncResultPanel";

function makeResult(overrides: Partial<SpreadsheetSyncResponse> = {}): SpreadsheetSyncResponse {
  return {
    imported_case_ids: ["case-1", "case-2"],
    imported_rows: [
      {
        sheet_row_id: "7",
        case_id: "case-1"
      }
    ],
    jobs: [],
    rejected_rows: [
      {
        row_index: 9,
        sheet_row_id: "row-9",
        error_message: "missing prompt"
      }
    ],
    ...overrides
  };
}

describe("SpreadsheetSyncResultPanel", () => {
  it("renders spreadsheet sync imported and rejected row summaries", () => {
    render(<SpreadsheetSyncResultPanel result={makeResult()} />);

    expect(screen.getByText("表格同步样本：2")).toBeInTheDocument();
    expect(screen.getByText("表格同步行：7:case-1")).toBeInTheDocument();
    expect(screen.getByText("表格同步拒绝：9:row-9:missing prompt")).toBeInTheDocument();
  });

  it("renders empty sync row summaries as none", () => {
    render(
      <SpreadsheetSyncResultPanel
        result={makeResult({
          imported_case_ids: [],
          imported_rows: [],
          rejected_rows: []
        })}
      />
    );

    expect(screen.getByText("表格同步样本：0")).toBeInTheDocument();
    expect(screen.getByText("表格同步行：无")).toBeInTheDocument();
    expect(screen.getByText("表格同步拒绝：无")).toBeInTheDocument();
  });

  it("renders auto-closure report links and writeback status from rerun results", () => {
    render(
      <SpreadsheetSyncResultPanel
        result={makeResult({
          jobs: [{ job_id: "job-131", case_id: "JSZN-131", status: "completed" }],
          auto_closure_reports: [
            {
              job_id: "job-131",
              case_id: "JSZN-131",
              closure: {
                source_job_id: "job-131",
                created_targeted_probe_jobs: ["job-probe-131"],
                created_strategy_follow_up_jobs: [],
                created_verification_jobs: ["job-verify-131"],
                evidence_summaries: [],
                targeted_probe_outcomes: [],
                final_attribution_candidates: [],
                badcase_live_comparison: {
                  original_badcase: "原 badcase：0/1 通过，avg_score=0.0。",
                  live_rerun: "Live 复测：0/1 通过，success_rate=0%。",
                  decision: "model_capability_gap"
                },
                writeback_status: "succeeded"
              },
              report_artifact_url: "/api/artifacts/files/JSZN-131_auto_closure_report.md",
              writeback_status: "succeeded"
            }
          ]
        })}
      />
    );

    expect(screen.getByText("表格闭环报告：1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "JSZN-131 自动闭环报告" })).toHaveAttribute(
      "href",
      "/api/artifacts/files/JSZN-131_auto_closure_report.md"
    );
    expect(screen.getByText("写回状态：成功")).toBeInTheDocument();
  });
});

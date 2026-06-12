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

    expect(screen.getByText("Spreadsheet 同步样本：2")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 同步行：7:case-1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 同步拒绝：9:row-9:missing prompt")).toBeInTheDocument();
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

    expect(screen.getByText("Spreadsheet 同步样本：0")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 同步行：无")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 同步拒绝：无")).toBeInTheDocument();
  });
});

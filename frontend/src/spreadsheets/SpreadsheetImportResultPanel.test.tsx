import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SpreadsheetRowImportResponse } from "../api/client";
import { SpreadsheetImportResultPanel } from "./SpreadsheetImportResultPanel";

function makeResult(overrides: Partial<SpreadsheetRowImportResponse> = {}): SpreadsheetRowImportResponse {
  return {
    imported_case_ids: ["case-1"],
    imported_rows: [
      {
        sheet_row_id: "sheet-row-1",
        case_id: "case-1"
      }
    ],
    jobs: [],
    rejected_rows: [
      {
        row_index: 3,
        sheet_row_id: "sheet-row-3",
        error_message: "missing image"
      }
    ],
    ...overrides
  };
}

describe("SpreadsheetImportResultPanel", () => {
  it("renders spreadsheet import row summaries", () => {
    render(<SpreadsheetImportResultPanel result={makeResult()} />);

    expect(screen.getByText("Spreadsheet 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入行：sheet-row-1:case-1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入拒绝：3:sheet-row-3:missing image")).toBeInTheDocument();
  });

  it("renders empty import row summaries as none", () => {
    render(
      <SpreadsheetImportResultPanel
        result={makeResult({
          imported_case_ids: [],
          imported_rows: [],
          rejected_rows: []
        })}
      />
    );

    expect(screen.getByText("Spreadsheet 导入样本：0")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入行：无")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入拒绝：无")).toBeInTheDocument();
  });
});

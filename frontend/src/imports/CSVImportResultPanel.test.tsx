import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CsvImportResponse } from "../api/client";
import { CSVImportResultPanel } from "./CSVImportResultPanel";

function makeResult(overrides: Partial<CsvImportResponse> = {}): CsvImportResponse {
  return {
    imported_case_ids: ["case-1"],
    jobs: [],
    rejected_rows: [
      {
        row_number: 4,
        error_message: "missing scoring standard"
      }
    ],
    ...overrides
  };
}

describe("CSVImportResultPanel", () => {
  it("renders imported case count and rejected row summaries", () => {
    render(<CSVImportResultPanel result={makeResult()} />);

    expect(screen.getByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：4:missing scoring standard")).toBeInTheDocument();
  });

  it("renders empty rejected row summaries as none", () => {
    render(
      <CSVImportResultPanel
        result={makeResult({
          imported_case_ids: [],
          rejected_rows: []
        })}
      />
    );

    expect(screen.getByText("CSV 导入样本：0")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：无")).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CsvImportResponse, JsonlImportResponse, SpreadsheetRowImportResponse } from "../api/client";
import { ImportWorkspace } from "./ImportWorkspace";

function makeJsonlResult(): JsonlImportResponse {
  return {
    imported_case_ids: ["case-jsonl-1"],
    jobs: [],
    rejected_lines: []
  };
}

function makeCsvResult(): CsvImportResponse {
  return {
    imported_case_ids: ["case-csv-1"],
    jobs: [],
    rejected_rows: []
  };
}

function makeSpreadsheetResult(): SpreadsheetRowImportResponse {
  return {
    imported_case_ids: ["case-sheet-1"],
    imported_rows: [{ sheet_row_id: "7", case_id: "case-sheet-1" }],
    jobs: [],
    rejected_rows: []
  };
}

describe("ImportWorkspace", () => {
  it("renders import sections, result summaries, and delegates actions", async () => {
    const onJsonlChange = vi.fn();
    const onCsvChange = vi.fn();
    const onSpreadsheetRowsJsonChange = vi.fn();
    const onImportJsonl = vi.fn();
    const onImportCsv = vi.fn();
    const onImportSpreadsheetRowsJson = vi.fn();

    render(
      <ImportWorkspace
        jsonlCases="{}"
        jsonlImportResult={makeJsonlResult()}
        csvCases="case_id,prompt"
        csvImportResult={makeCsvResult()}
        spreadsheetRowsJson="[]"
        spreadsheetImportResult={makeSpreadsheetResult()}
        onJsonlChange={onJsonlChange}
        onCsvChange={onCsvChange}
        onSpreadsheetRowsJsonChange={onSpreadsheetRowsJsonChange}
        onImportJsonl={onImportJsonl}
        onImportCsv={onImportCsv}
        onImportSpreadsheetRowsJson={onImportSpreadsheetRowsJson}
      />
    );

    expect(screen.getByRole("heading", { name: "JSONL Import" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CSV Import" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spreadsheet Rows Import" })).toBeInTheDocument();
    expect(screen.getByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入样本：1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("JSONL cases"), { target: { value: "{\"case_id\":\"case-2\"}" } });
    fireEvent.change(screen.getByLabelText("CSV cases"), { target: { value: "case_id\ncase-2" } });
    fireEvent.change(screen.getByLabelText("Spreadsheet rows JSON"), { target: { value: "[{}]" } });
    await userEvent.click(screen.getByRole("button", { name: "Import JSONL cases" }));
    await userEvent.click(screen.getByRole("button", { name: "Import CSV cases" }));
    await userEvent.click(screen.getByRole("button", { name: "Import spreadsheet rows JSON" }));

    expect(onJsonlChange).toHaveBeenCalledWith("{\"case_id\":\"case-2\"}");
    expect(onCsvChange).toHaveBeenCalledWith("case_id\ncase-2");
    expect(onSpreadsheetRowsJsonChange).toHaveBeenCalledWith("[{}]");
    expect(onImportJsonl).toHaveBeenCalledTimes(1);
    expect(onImportCsv).toHaveBeenCalledTimes(1);
    expect(onImportSpreadsheetRowsJson).toHaveBeenCalledTimes(1);
  });
});

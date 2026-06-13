import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetRowImportResponse } from "../api/client";
import { SpreadsheetImportPanel } from "./SpreadsheetImportPanel";

function makeResult(overrides: Partial<SpreadsheetRowImportResponse> = {}): SpreadsheetRowImportResponse {
  return {
    imported_case_ids: ["case-1"],
    imported_rows: [{ sheet_row_id: "row-1", case_id: "case-1" }],
    jobs: [],
    rejected_rows: [],
    ...overrides
  };
}

describe("SpreadsheetImportPanel", () => {
  it("renders controls, delegates changes, and shows import result", async () => {
    const onChange = vi.fn();
    const onImport = vi.fn();

    render(<SpreadsheetImportPanel value='[{"row_id":"1"}]' result={makeResult()} onChange={onChange} onImport={onImport} />);

    fireEvent.change(screen.getByLabelText("Spreadsheet rows JSON"), { target: { value: '[{"row_id":"2"}]' } });
    await userEvent.click(screen.getByRole("button", { name: "Import spreadsheet rows JSON" }));

    expect(onChange).toHaveBeenCalledWith('[{"row_id":"2"}]');
    expect(onImport).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Spreadsheet 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入行：row-1:case-1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入拒绝：无")).toBeInTheDocument();
  });

  it("hides import result before an import has completed", () => {
    render(<SpreadsheetImportPanel value="" result={null} onChange={vi.fn()} onImport={vi.fn()} />);

    expect(screen.queryByText(/Spreadsheet 导入样本/)).not.toBeInTheDocument();
  });
});

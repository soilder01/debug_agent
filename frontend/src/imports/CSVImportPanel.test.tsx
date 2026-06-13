import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CsvImportResponse } from "../api/client";
import { CSVImportPanel } from "./CSVImportPanel";

function makeResult(overrides: Partial<CsvImportResponse> = {}): CsvImportResponse {
  return {
    imported_case_ids: ["case-1"],
    jobs: [],
    rejected_rows: [],
    ...overrides
  };
}

describe("CSVImportPanel", () => {
  it("renders controls, delegates changes, and shows import result", async () => {
    const onChange = vi.fn();
    const onImport = vi.fn();

    render(<CSVImportPanel value="case_id,image_uri" result={makeResult()} onChange={onChange} onImport={onImport} />);

    fireEvent.change(screen.getByLabelText("CSV cases"), { target: { value: "case_id,image_uri\ncase-2,img.png" } });
    await userEvent.click(screen.getByRole("button", { name: "Import CSV cases" }));

    expect(onChange).toHaveBeenCalledWith("case_id,image_uri\ncase-2,img.png");
    expect(onImport).toHaveBeenCalledTimes(1);
    expect(screen.getByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：无")).toBeInTheDocument();
  });

  it("hides import result before an import has completed", () => {
    render(<CSVImportPanel value="" result={null} onChange={vi.fn()} onImport={vi.fn()} />);

    expect(screen.queryByText(/CSV 导入样本/)).not.toBeInTheDocument();
  });
});

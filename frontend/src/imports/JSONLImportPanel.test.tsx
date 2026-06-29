import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { JsonlImportResponse } from "../api/client";
import { JSONLImportPanel } from "./JSONLImportPanel";

function makeResult(overrides: Partial<JsonlImportResponse> = {}): JsonlImportResponse {
  return {
    imported_case_ids: ["case-1"],
    jobs: [],
    rejected_lines: [],
    ...overrides
  };
}

describe("JSONLImportPanel", () => {
  it("renders controls, delegates changes, and shows import result", async () => {
    const onChange = vi.fn();
    const onImport = vi.fn();

    render(<JSONLImportPanel value='{"case_id":"case-1"}' result={makeResult()} onChange={onChange} onImport={onImport} />);

    fireEvent.change(screen.getByLabelText("JSONL 案件数据"), { target: { value: '{"case_id":"case-2"}' } });
    await userEvent.click(screen.getByRole("button", { name: "导入 JSONL 案件" }));

    expect(onChange).toHaveBeenCalledWith('{"case_id":"case-2"}');
    expect(onImport).toHaveBeenCalledTimes(1);
    expect(screen.getByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：无")).toBeInTheDocument();
  });

  it("hides import result before an import has completed", () => {
    render(<JSONLImportPanel value="" result={null} onChange={vi.fn()} onImport={vi.fn()} />);

    expect(screen.queryByText(/导入样本/)).not.toBeInTheDocument();
  });
});

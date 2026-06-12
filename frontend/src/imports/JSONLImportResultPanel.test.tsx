import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { JsonlImportResponse } from "../api/client";
import { JSONLImportResultPanel } from "./JSONLImportResultPanel";

function makeResult(overrides: Partial<JsonlImportResponse> = {}): JsonlImportResponse {
  return {
    imported_case_ids: ["case-1"],
    jobs: [],
    rejected_lines: [
      {
        line_number: 3,
        error_message: "invalid json"
      }
    ],
    ...overrides
  };
}

describe("JSONLImportResultPanel", () => {
  it("renders imported case count and rejected line summaries", () => {
    render(<JSONLImportResultPanel result={makeResult()} />);

    expect(screen.getByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：3:invalid json")).toBeInTheDocument();
  });

  it("renders empty rejected line summaries as none", () => {
    render(
      <JSONLImportResultPanel
        result={makeResult({
          imported_case_ids: [],
          rejected_lines: []
        })}
      />
    );

    expect(screen.getByText("导入样本：0")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：无")).toBeInTheDocument();
  });
});

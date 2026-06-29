import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugCaseDetail, DebugCaseSummary } from "../api/client";
import { ImportedCasesPanel } from "./ImportedCasesPanel";

function makeCaseSummary(overrides: Partial<DebugCaseSummary> = {}): DebugCaseSummary {
  return {
    case_id: "case-1",
    image_uri: "https://debug-agent.local/case-1.png",
    avg_score: 0.5,
    debug_status: "",
    root_cause: "",
    box_region_count: 1,
    ...overrides
  };
}

function makeCaseDetail(overrides: Partial<DebugCaseDetail> = {}): DebugCaseDetail {
  return {
    case_id: "case-1",
    image_uri: "https://debug-agent.local/case-1.png",
    prompt: "Read answer",
    golden_answer: { answers: [{ box_id: 1, student_answer: "42" }] },
    scoring_standard: "exact",
    predictions: [{ trial: 1, raw_output: "42", score: 1 }],
    avg_score: 1,
    human_notes: { debug_status: "pending", root_cause: "" },
    box_regions: [],
    ...overrides
  };
}

describe("ImportedCasesPanel", () => {
  it("renders heading and delegates initial load action", async () => {
    const onLoadImportedCases = vi.fn();

    render(
      <ImportedCasesPanel
        cases={[]}
        totalCount={0}
        effectiveCount={0}
        unloadedCount={0}
        selectedCaseDetail={null}
        onLoadImportedCases={onLoadImportedCases}
        onLoadWithRegions={vi.fn()}
        onLoadAll={vi.fn()}
        onLoadMore={vi.fn()}
        onUseForBatch={vi.fn()}
        onViewCaseDetail={vi.fn()}
        onCreateDebugJob={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "导入样本" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "导入样本" })).toHaveClass("case-queue");
    expect(screen.getByText("先加载导入样本，再启动定向 debug 任务。")).toBeInTheDocument();
    expect(screen.getByText("尚未加载导入样本")).toBeInTheDocument();
    expect(screen.queryByLabelText("导入样本摘要")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "加载导入样本" }));

    expect(onLoadImportedCases).toHaveBeenCalledTimes(1);
  });

  it("renders imported case list and selected case detail", () => {
    render(
      <ImportedCasesPanel
        cases={[makeCaseSummary()]}
        totalCount={1}
        effectiveCount={1}
        unloadedCount={0}
        selectedCaseDetail={makeCaseDetail()}
        onLoadImportedCases={vi.fn()}
        onLoadWithRegions={vi.fn()}
        onLoadAll={vi.fn()}
        onLoadMore={vi.fn()}
        onUseForBatch={vi.fn()}
        onViewCaseDetail={vi.fn()}
        onCreateDebugJob={vi.fn()}
      />
    );

    expect(screen.getByText("已导入样本：1")).toBeInTheDocument();
    expect(screen.getByLabelText("导入样本队列指标")).toBeInTheDocument();
    expect(screen.getByText("case-1｜平均分 0.5｜区域 1｜未标记｜未归因")).toBeInTheDocument();
    expect(screen.getByText("样本详情：case-1")).toBeInTheDocument();
  });
});

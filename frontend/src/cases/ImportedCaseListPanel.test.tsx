import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugCaseSummary } from "../api/client";
import { ImportedCaseListPanel } from "./ImportedCaseListPanel";

function makeCase(overrides: Partial<DebugCaseSummary> = {}): DebugCaseSummary {
  return {
    case_id: "case-1",
    image_uri: "https://debug-agent.local/case-1.png",
    avg_score: 0.4,
    debug_status: "",
    root_cause: "",
    box_region_count: 2,
    ...overrides
  };
}

describe("ImportedCaseListPanel", () => {
  it("renders imported case counts and delegates list actions", async () => {
    const onLoadWithRegions = vi.fn();
    const onLoadAll = vi.fn();
    const onLoadMore = vi.fn();
    const onUseForBatch = vi.fn();
    const onViewCaseDetail = vi.fn();

    render(
      <ImportedCaseListPanel
        cases={[makeCase()]}
        totalCount={5}
        effectiveCount={3}
        unloadedCount={2}
        onLoadWithRegions={onLoadWithRegions}
        onLoadAll={onLoadAll}
        onLoadMore={onLoadMore}
        onUseForBatch={onUseForBatch}
        onViewCaseDetail={onViewCaseDetail}
      />
    );

    expect(screen.getByText("已导入样本：5")).toBeInTheDocument();
    expect(screen.getByText("已显示样本：1/3")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：2")).toBeInTheDocument();
    expect(screen.getByLabelText("导入样本队列指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("样本队列操作")).toHaveClass("action-row");
    expect(screen.getByText("case-1｜平均分 0.4｜区域 2｜未标记｜未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "只看有区域的样本" }));
    await userEvent.click(screen.getByRole("button", { name: "显示全部导入样本" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多导入样本" }));
    await userEvent.click(screen.getByRole("button", { name: "用导入样本创建批次" }));
    await userEvent.click(screen.getByRole("button", { name: "查看样本详情 case-1" }));

    expect(onLoadWithRegions).toHaveBeenCalledTimes(1);
    expect(onLoadAll).toHaveBeenCalledTimes(1);
    expect(onLoadMore).toHaveBeenCalledTimes(1);
    expect(onUseForBatch).toHaveBeenCalledTimes(1);
    expect(onViewCaseDetail).toHaveBeenCalledWith("case-1");
  });

  it("hides load more when all imported cases are loaded", () => {
    render(
      <ImportedCaseListPanel
        cases={[makeCase({ case_id: "case-loaded" })]}
        totalCount={1}
        effectiveCount={1}
        unloadedCount={0}
        onLoadWithRegions={vi.fn()}
        onLoadAll={vi.fn()}
        onLoadMore={vi.fn()}
        onUseForBatch={vi.fn()}
        onViewCaseDetail={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: "加载更多导入样本" })).not.toBeInTheDocument();
  });

  it("falls back to safe count values when upstream totals are unavailable", () => {
    render(
      <ImportedCaseListPanel
        cases={[makeCase({ case_id: "case-safe" })]}
        totalCount={undefined as unknown as number}
        effectiveCount={undefined as unknown as number}
        unloadedCount={undefined as unknown as number}
        onLoadWithRegions={vi.fn()}
        onLoadAll={vi.fn()}
        onLoadMore={vi.fn()}
        onUseForBatch={vi.fn()}
        onViewCaseDetail={vi.fn()}
      />
    );

    expect(screen.queryByText("NaN")).not.toBeInTheDocument();
    expect(screen.getByText("已导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("已显示样本：1/1")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：0")).toBeInTheDocument();
  });
});

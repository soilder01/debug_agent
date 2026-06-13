import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugCaseDetail } from "../api/client";
import { ImportedCaseDetailPanel } from "./ImportedCaseDetailPanel";

function makeCaseDetail(overrides: Partial<DebugCaseDetail> = {}): DebugCaseDetail {
  return {
    case_id: "case-detail-1",
    image_uri: "https://debug-agent.local/case-detail-1.png",
    prompt: "Read the handwritten answer",
    golden_answer: {
      answers: [{ box_id: 1, student_answer: "42" }]
    },
    scoring_standard: "score exactly",
    predictions: [{ trial: 1, raw_output: "41", score: 0 }],
    avg_score: 0,
    human_notes: {
      debug_status: "",
      root_cause: ""
    },
    box_regions: [
      {
        box_id: 1,
        x: 10,
        y: 20,
        width: 30,
        height: 40,
        unit: "px",
        label: ""
      }
    ],
    ...overrides
  };
}

describe("ImportedCaseDetailPanel", () => {
  it("renders selected case detail and delegates submit action", async () => {
    const onCreateDebugJob = vi.fn();

    render(<ImportedCaseDetailPanel caseDetail={makeCaseDetail()} onCreateDebugJob={onCreateDebugJob} />);

    expect(screen.getByText("样本详情：case-detail-1")).toBeInTheDocument();
    expect(screen.getByText("图片：https://debug-agent.local/case-detail-1.png")).toBeInTheDocument();
    expect(screen.getByText("Prompt：Read the handwritten answer")).toBeInTheDocument();
    expect(screen.getByText("评分标准：score exactly")).toBeInTheDocument();
    expect(screen.getByText("标答 1：42")).toBeInTheDocument();
    expect(screen.getByText("区域 1：x=10, y=20, width=30, height=40, unit=px, label=无")).toBeInTheDocument();
    expect(screen.getByText("预测 trial 1：score 0")).toBeInTheDocument();
    expect(screen.getByText("人工状态：未标记")).toBeInTheDocument();
    expect(screen.getByText("人工根因：未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Create debug job for case-detail-1" }));

    expect(onCreateDebugJob).toHaveBeenCalledWith("case-detail-1");
  });

  it("hides box regions when no regions are available", () => {
    render(<ImportedCaseDetailPanel caseDetail={makeCaseDetail({ box_regions: [] })} onCreateDebugJob={vi.fn()} />);

    expect(screen.queryByLabelText("Box regions")).not.toBeInTheDocument();
  });
});

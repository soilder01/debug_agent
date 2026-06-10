import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("runs single-case debug and renders report", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          case_id: "handwrite233",
          status: "needs_human_review",
          observed_failure: {
            type: "erasure_revision_failure",
            summary: "",
            affected_box_ids: [1]
          },
          planned_experiments: ["baseline_replay"],
          experiment_summary: {
            total_trials: 6,
            success_count: 0,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          },
          root_cause: {
            label: "erasure_revision_failure",
            confidence: "medium",
            evidence_summary: "evidence"
          },
          suggested_sheet_fields: { "debug1状态": "待人工确认" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Run single-case debug" }));

    expect(await screen.findByText("样本 ID：handwrite233")).toBeInTheDocument();
    expect(screen.getByText("baseline_replay")).toBeInTheDocument();
    expect(screen.getByText(/成功次数：0 \/ 6/)).toBeInTheDocument();
    expect(screen.getByText(/类型：\s*erasure_revision_failure/)).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("submits a single-case debug job and renders the created job state", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "created",
            attempt_count: 0,
            error_message: null,
            evidence_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Submit debug job" }));

    expect(await screen.findByText("样本 ID：handwrite233")).toBeInTheDocument();
    expect(screen.getByText("Job ID：job-123")).toBeInTheDocument();
    expect(screen.getByText("状态：created")).toBeInTheDocument();
    expect(screen.getByText("尝试次数：0")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/cases/handwrite233/debug-jobs?auto_run=true", {
      method: "POST"
    });

    expect(await screen.findByText("状态：completed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("尝试次数：1")).toBeInTheDocument();
    expect(screen.getByText("证据数：1")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-123");
  });
});

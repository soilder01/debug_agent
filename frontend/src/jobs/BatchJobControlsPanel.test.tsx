import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BatchJobControlsPanel } from "./BatchJobControlsPanel";

describe("BatchJobControlsPanel", () => {
  it("renders batch controls and delegates actions", async () => {
    const onCaseIdsChange = vi.fn();
    const onSubmit = vi.fn();
    const onLoadJobs = vi.fn();

    render(
      <BatchJobControlsPanel
        caseIds="case-1"
        onCaseIdsChange={onCaseIdsChange}
        onSubmit={onSubmit}
        onLoadJobs={onLoadJobs}
      />
    );

    expect(screen.getByRole("heading", { name: "Batch Jobs" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Batch case ids"), { target: { value: "case-1\ncase-2" } });

    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));
    await userEvent.click(screen.getByRole("button", { name: "Load debug jobs" }));
    await userEvent.click(screen.getByRole("button", { name: "Load failed jobs" }));
    await userEvent.click(screen.getByRole("button", { name: "Load newest debug jobs" }));

    expect(onCaseIdsChange).toHaveBeenCalledWith("case-1\ncase-2");
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onLoadJobs).toHaveBeenNthCalledWith(1, undefined, undefined);
    expect(onLoadJobs).toHaveBeenNthCalledWith(2, "failed", undefined);
    expect(onLoadJobs).toHaveBeenNthCalledWith(3, undefined, "created_at_desc");
  });
});

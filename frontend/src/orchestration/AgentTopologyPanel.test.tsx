import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { AgentTopologyPanel } from "./AgentTopologyPanel";

afterEach(() => {
  cleanup();
});

describe("AgentTopologyPanel", () => {
  it("renders seven logical agent capabilities", () => {
    render(<AgentTopologyPanel />);

    expect(screen.getByRole("heading", { name: "Agent Topology" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
    expect(screen.getByText("Case Intake Agent")).toBeInTheDocument();
    expect(screen.getByText("Experiment Planner Agent")).toBeInTheDocument();
    expect(screen.getByText("Model Runner Agent")).toBeInTheDocument();
    expect(screen.getByText("Judge Comparator Agent")).toBeInTheDocument();
    expect(screen.getByText("Evidence Artifact Agent")).toBeInTheDocument();
    expect(screen.getByText("Report Root Cause Agent")).toBeInTheDocument();
    expect(screen.getByText("Writeback Operator Agent")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ActionRow,
  EmptyState,
  MetricStrip,
  ProductSurface,
  SectionHeader,
  StatusBadge
} from "./ProductPrimitives";

describe("ProductPrimitives", () => {
  it("renders a labelled product surface region", () => {
    render(
      <ProductSurface title="Investigation queue" eyebrow="Operations" description="Active debug work">
        <button type="button">Open queue</button>
      </ProductSurface>
    );

    const region = screen.getByRole("region", { name: "Investigation queue" });
    expect(region).toHaveClass("product-surface");
    expect(screen.getByText("Operations")).toHaveClass("section-header__eyebrow");
    expect(screen.getByText("Active debug work")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open queue" })).toBeInTheDocument();
  });

  it("renders metric labels and values in a definition list", () => {
    render(
      <MetricStrip
        metrics={[
          { label: "Open jobs", value: 12 },
          { label: "Recovery reopen", value: "3" }
        ]}
      />
    );

    expect(screen.getByLabelText("Metrics")).toHaveClass("metric-strip");
    expect(screen.getByText("Open jobs")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Recovery reopen")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("maps status tones to stable badge class names", () => {
    render(
      <>
        <StatusBadge tone="critical">Critical</StatusBadge>
        <StatusBadge tone="warning">Warning</StatusBadge>
        <StatusBadge tone="success">Success</StatusBadge>
        <StatusBadge tone="neutral">Neutral</StatusBadge>
      </>
    );

    expect(screen.getByText("Critical")).toHaveClass("status-badge--critical");
    expect(screen.getByText("Warning")).toHaveClass("status-badge--warning");
    expect(screen.getByText("Success")).toHaveClass("status-badge--success");
    expect(screen.getByText("Neutral")).toHaveClass("status-badge--neutral");
  });

  it("renders action rows, empty states, and standalone section headers", () => {
    render(
      <>
        <SectionHeader eyebrow="Evidence" title="No evidence selected" description="Select a run to inspect details." />
        <ActionRow>
          <button type="button">Select evidence</button>
        </ActionRow>
        <EmptyState title="Nothing loaded" description="Load a report to begin." />
      </>
    );

    expect(screen.getByRole("heading", { name: "No evidence selected" })).toBeInTheDocument();
    expect(screen.getByLabelText("Actions")).toHaveClass("action-row");
    expect(screen.getByRole("button", { name: "Select evidence" })).toBeInTheDocument();
    expect(screen.getByText("Nothing loaded")).toHaveClass("empty-state__title");
    expect(screen.getByText("Load a report to begin.")).toBeInTheDocument();
  });
});

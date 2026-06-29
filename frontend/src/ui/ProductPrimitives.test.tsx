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
      <ProductSurface title="调查队列" eyebrow="操作" description="当前 debug 工作">
        <button type="button">打开队列</button>
      </ProductSurface>
    );

    const region = screen.getByRole("region", { name: "调查队列" });
    expect(region).toHaveClass("product-surface");
    expect(screen.getByText("操作")).toHaveClass("section-header__eyebrow");
    expect(screen.getByText("当前 debug 工作")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打开队列" })).toBeInTheDocument();
  });

  it("renders metric labels and values in a definition list", () => {
    render(
      <MetricStrip
        metrics={[
          { label: "打开任务", value: 12 },
          { label: "恢复重开", value: "3" }
        ]}
      />
    );

    expect(screen.getByLabelText("指标")).toHaveClass("metric-strip");
    expect(screen.getByText("打开任务")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("恢复重开")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("maps status tones to stable badge class names", () => {
    render(
      <>
        <StatusBadge tone="critical">严重</StatusBadge>
        <StatusBadge tone="warning">警告</StatusBadge>
        <StatusBadge tone="success">成功</StatusBadge>
        <StatusBadge tone="neutral">普通</StatusBadge>
      </>
    );

    expect(screen.getByText("严重")).toHaveClass("status-badge--critical");
    expect(screen.getByText("警告")).toHaveClass("status-badge--warning");
    expect(screen.getByText("成功")).toHaveClass("status-badge--success");
    expect(screen.getByText("普通")).toHaveClass("status-badge--neutral");
  });

  it("renders action rows, empty states, and standalone section headers", () => {
    render(
      <>
        <SectionHeader eyebrow="证据" title="未选择证据" description="选择一次运行后查看详情。" />
        <ActionRow>
          <button type="button">选择证据</button>
        </ActionRow>
        <EmptyState title="尚未加载" description="先加载报告再开始。" />
      </>
    );

    expect(screen.getByRole("heading", { name: "未选择证据" })).toBeInTheDocument();
    expect(screen.getByLabelText("操作")).toHaveClass("action-row");
    expect(screen.getByRole("button", { name: "选择证据" })).toBeInTheDocument();
    expect(screen.getByText("尚未加载")).toHaveClass("empty-state__title");
    expect(screen.getByText("先加载报告再开始。")).toBeInTheDocument();
  });
});

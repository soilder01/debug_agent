import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PilotGate } from "../api/client";
import { PilotGatePanel } from "./PilotGatePanel";

function makeGate(): PilotGate {
  return {
    generated_at: "2026-06-22T00:00:00+00:00",
    status: "warning",
    thresholds: {
      min_completed_jobs: 20,
      min_success_rate: 0.8,
      max_p95_duration_ms: 12000,
      max_estimated_cost_units: 100,
      max_model_call_errors: 0,
      max_writeback_failed: 0,
      max_lark_operation_failures: 0
    },
    batch_evidence: {
      compared_batch_count: 2,
      completed_jobs: 18,
      best_batch_id: "batch-a",
      best_success_rate: 0.9,
      best_p95_duration_ms: 9000,
      best_estimated_cost_units: 12.5,
      best_quality_score: 88,
      best_efficiency_score: 77
    },
    checks: [
      {
        key: "scale_coverage",
        label: "真实样本覆盖",
        status: "failed",
        detail: "completed_jobs=18, required=20",
        action: "继续执行 operator-approved 真实批次。"
      },
      {
        key: "production_readiness",
        label: "生产运行就绪",
        status: "warning",
        detail: "readiness=degraded",
        action: "先处理 readiness warning 项。"
      }
    ],
    comparison: {
      generated_at: "2026-06-22T00:00:00+00:00",
      batch_ids: ["batch-a", "batch-b"],
      items: [],
      best_batch_id: "batch-a",
      summary: "推荐 batch-a",
      export_url: "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b"
    },
    export_urls: {
      readiness: "/api/operations/readiness",
      batch_comparison: "/api/debug-batches/comparison",
      batch_comparison_csv: "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b",
      support_bundle: "/api/operations/support-bundle.zip"
    }
  };
}

describe("PilotGatePanel", () => {
  it("renders pilot gate status, checks, and exports", () => {
    render(<PilotGatePanel gate={makeGate()} />);

    expect(screen.getByRole("heading", { name: "试点准入评估" })).toBeInTheDocument();
    expect(screen.getByText("试点准入状态：需关注")).toBeInTheDocument();
    expect(screen.getByText("试点准入最佳批次：batch-a")).toBeInTheDocument();
    expect(screen.getByLabelText("试点准入核心指标")).toHaveClass("metric-strip");
    expect(screen.getByText(/真实样本覆盖：阻塞/)).toBeInTheDocument();
    expect(screen.getByText(/生产运行就绪：需关注/)).toBeInTheDocument();
    expect(screen.getByText("批次 A/B CSV：/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b")).toBeInTheDocument();
    expect(screen.getByText("运维支持包：/api/operations/support-bundle.zip")).toBeInTheDocument();
  });
});

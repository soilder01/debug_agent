import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ObservabilitySummary } from "../api/client";
import { ObservabilitySummaryPanel } from "./ObservabilitySummaryPanel";

function makeSummary(): ObservabilitySummary {
  return {
    jobs: {
      by_status: {
        created: 4,
        running: 1,
        completed: 12,
        failed: 2
      },
      total_count: 19,
      pending_count: 4,
      running_count: 1,
      failed_count: 2,
      completed_count: 12
    },
    worker: {
      running: true,
      processed_count: 18,
      error_count: 1,
      last_error: "hook failed",
      completion_hook_enabled: true,
      report_base_url: "https://debug-agent.local",
      auto_writeback_enabled: true
    },
    writeback_audits: {
      by_status: {
        succeeded: 10,
        failed: 2,
        skipped: 1
      },
      total_count: 13
    },
    evidence: {
      total_evidence: 42,
      failed_judgements: 11,
      response_parse_errors: 3,
      model_call_errors: 2,
      average_latency_ms: 88.5
    },
    usage: {
      model_call_count: 42,
      prompt_character_count: 12345,
      estimated_cost_units: 54.345,
      budget_units: 50,
      budget_status: "over_budget",
      budget_utilization: 1.0869,
      budget_enforcement_enabled: true
    },
    strategy_feedback: {
      total_follow_ups: 6,
      pending_count: 2,
      passed_stop_condition_count: 3,
      needs_escalation_count: 1
    },
    targeted_probe_feedback: {
      total_probes: 5,
      pending_count: 1,
      target_cleared_count: 2,
      target_still_failing_count: 1,
      inconclusive_count: 1,
      max_depth_reached_count: 1
    },
    human_handoff_feedback: {
      total_handoffs: 3,
      pending_count: 1,
      acknowledged_count: 0,
      in_progress_count: 1,
      resolved_count: 1,
      wont_fix_count: 0,
      open_count: 2
    },
    final_attribution_verification_feedback: {
      total_verifications: 4,
      pending_count: 1,
      resolved_count: 1,
      not_resolved_count: 2,
      inconclusive_count: 0
    },
    final_attribution_recovery_feedback: {
      total_recoveries: 5,
      pending_count: 1,
      closed_count: 2,
      reopen_count: 1,
      inconclusive_count: 1
    },
    health: {
      level: "critical",
      reasons: [
        "failed jobs present",
        "worker errors present",
        "failed spreadsheet writebacks present",
        "model call errors present",
        "usage budget exceeded",
        "pending jobs present",
        "jobs currently running",
        "response parse errors present",
        "skipped spreadsheet writebacks present",
        "strategy follow-ups need escalation",
        "targeted probes still failing",
        "targeted probe guardrails reached",
        "human handoffs still open",
        "final attribution verifications not resolved",
        "final attribution recoveries reopened"
      ],
      actions: [
        "Inspect failed jobs and open their evidence chain.",
        "Check worker logs and restart the worker if the error persists.",
        "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers.",
        "Check model endpoint health, timeout settings, and retry affected jobs.",
        "Pause new submissions or raise the usage budget before continuing.",
        "Start or scale workers to drain the pending job backlog.",
        "Monitor running jobs for timeout or stuck execution.",
        "Inspect prompts and parser assumptions for malformed model outputs.",
        "Check spreadsheet row mappings before retrying writeback.",
        "Open strategy follow-up history and run escalation probes.",
        "Open targeted probe history and escalate unresolved targets.",
        "Review targeted probe guardrails and assign human investigation.",
        "Review human handoff queue and drive open investigations to resolution.",
        "Open final attribution verification results and rerun unresolved attribution fixes.",
        "Open final attribution recovery results and reassign reopened attribution review."
      ]
    },
    performance: {
      total_count: 4,
      aggregates: [
        {
          component: "api",
          operation: "GET /jobs/{job_id}/report",
          count: 2,
          failed_count: 0,
          avg_ms: 20,
          p50_ms: 18,
          p95_ms: 35,
          max_ms: 35,
          latest_ms: 35
        },
        {
          component: "lark_cli",
          operation: "+csv-get",
          count: 1,
          failed_count: 0,
          avg_ms: 120,
          p50_ms: 120,
          p95_ms: 120,
          max_ms: 120,
          latest_ms: 120
        },
        {
          component: "writeback",
          operation: "write_report_to_spreadsheet_row",
          count: 1,
          failed_count: 0,
          avg_ms: 80,
          p50_ms: 80,
          p95_ms: 80,
          max_ms: 80,
          latest_ms: 80
        }
      ],
      recent_events: [
        {
          component: "api",
          operation: "GET /jobs/{job_id}/report",
          duration_ms: 35,
          status: "succeeded",
          metadata: { status_code: 200 },
          occurred_at: "2026-06-22T00:00:00+00:00"
        }
      ]
    }
  };
}

describe("ObservabilitySummaryPanel", () => {
  it("renders job, worker, and writeback operational metrics", async () => {
    const onLoadFailedJobs = vi.fn();
    const onLoadFailedWritebacks = vi.fn();
    const onStartWorker = vi.fn();
    const onClose = vi.fn();

    render(
      <ObservabilitySummaryPanel
        summary={makeSummary()}
        onLoadFailedJobs={onLoadFailedJobs}
        onLoadFailedWritebacks={onLoadFailedWritebacks}
        onStartWorker={onStartWorker}
        onClose={onClose}
      />
    );

    expect(screen.getByRole("heading", { name: "监控概览" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "监控概览" })).toHaveClass("observability-dashboard");
    expect(screen.getByRole("region", { name: "监控概览" })).toHaveClass("observability-dashboard--compact");
    expect(screen.getByRole("region", { name: "监控详情卡片" })).toHaveClass("observability-dashboard__grid");
    expect(screen.getByLabelText("任务队列指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("后台进程指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("证据质量指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("资源消耗指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("策略与针对性反馈指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("归因验证与恢复指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("性能基线指标")).toHaveClass("metric-strip");
    expect(screen.getByLabelText("健康操作")).toHaveClass("action-row");
    expect(screen.getByText("严重")).toHaveClass("status-badge--critical");
    expect(screen.getByText("超预算")).toHaveClass("status-badge--critical");
    expect(screen.getByText("任务总数：19")).toBeInTheDocument();
    expect(screen.getByText("后台进程运行中：是")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("后台进程最近错误：hook failed");
    expect(screen.getByText("回写审计总数：13")).toBeInTheDocument();
    expect(screen.getByText("证据模型调用错误：2")).toBeInTheDocument();
    expect(screen.getByText("预算状态：超预算")).toBeInTheDocument();
    expect(screen.getByText("策略需升级：1")).toBeInTheDocument();
    expect(screen.getByText("定向达到最大深度：1")).toBeInTheDocument();
    expect(screen.getByText("最终归因未解决：2")).toBeInTheDocument();
    expect(screen.getByText("性能记录数：4")).toBeInTheDocument();
    expect(screen.getByText("API P95：35ms")).toBeInTheDocument();
    expect(screen.getByText("Lark P95：120ms")).toBeInTheDocument();
    expect(screen.getByText("写回 P95：80ms")).toBeInTheDocument();
    expect(screen.getByText("最近性能事件：api/GET /jobs/{job_id}/report/35ms/已成功")).toBeInTheDocument();
    expect(screen.getByText("健康状态：严重")).toBeInTheDocument();
    expect(screen.getAllByText("健康原因：存在失败任务").length).toBeGreaterThan(0);
    expect(screen.getAllByText("健康原因：存在等待处理任务").length).toBeGreaterThan(0);
    expect(screen.getAllByText("健康原因：存在跳过的表格回写").length).toBeGreaterThan(0);
    expect(screen.getAllByText("健康原因：存在失败的表格回写").length).toBeGreaterThan(0);
    expect(screen.getAllByText("健康原因：最终归因恢复被重新开启").length).toBeGreaterThan(0);
    expect(screen.getAllByText("建议操作：检查失败任务并打开对应证据链。").length).toBeGreaterThan(0);
    expect(screen.getAllByText("建议操作：启动或扩容后台进程，处理等待任务积压。").length).toBeGreaterThan(0);
    expect(screen.getAllByText("建议操作：重试写回前检查表格行映射。").length).toBeGreaterThan(0);
    expect(screen.getAllByText("建议操作：确认飞书权限和表头后重试失败回写。").length).toBeGreaterThan(0);
    expect(screen.getAllByText("建议操作：打开策略跟进历史并执行升级探测。").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "打开监控中的失败任务" }));
    await userEvent.click(screen.getByRole("button", { name: "打开监控中的失败回写" }));
    await userEvent.click(screen.getByRole("button", { name: "从监控概览启动后台进程" }));
    await userEvent.click(screen.getByRole("button", { name: "收起监控概览" }));

    expect(onLoadFailedJobs).toHaveBeenCalledTimes(1);
    expect(onLoadFailedWritebacks).toHaveBeenCalledTimes(1);
    expect(onStartWorker).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

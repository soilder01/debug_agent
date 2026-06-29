import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DebugBatchEvaluationSummary, DebugBatchProgress, DebugJobStatus } from "../api/client";
import { BatchJobListPanel } from "./BatchJobListPanel";

function makeJob(overrides: Partial<DebugJobStatus> = {}): DebugJobStatus {
  return {
    job_id: "job-batch-1",
    case_id: "case-1",
    status: "failed",
    created_at: "2026-06-12T10:00:01Z",
    updated_at: "2026-06-12T10:00:02Z",
    attempt_count: 1,
    max_attempts: 2,
    remaining_attempts: 1,
    will_retry: true,
    retry_recommendation: "retry_model_call_error",
    retry_recommendation_detail: {
      code: "retry_model_call_error",
      label: "模型调用错误，建议重试",
      action: "重新排队该任务。",
      severity: "warning"
    },
    error_message: "transient error",
    evidence_ids: ["ev-1"],
    evidence_error_counts: {
      total_evidence: 1,
      failed_judgements: 0,
      response_parse_errors: 0,
      model_call_errors: 1
    },
    spreadsheet_writeback_audit: null,
    ...overrides
  };
}

function makeBatchProgress(
  batchId: string,
  overrides: Partial<DebugBatchEvaluationSummary> = {}
): DebugBatchProgress {
  const evaluation = {
    row_count: 5,
    created_jobs: 5,
    completed_jobs: 5,
    failed_jobs: 0,
    pending_jobs: 0,
    running_jobs: 0,
    success_rate: 1,
    failure_rate: 0,
    average_duration_ms: 100,
    p50_duration_ms: 90,
    p95_duration_ms: 120,
    max_duration_ms: 150,
    retry_scheduled_count: 0,
    model_call_count: 5,
    model_call_errors: 0,
    estimated_cost_units: 0.5,
    writeback_succeeded: 5,
    writeback_failed: 0,
    writeback_skipped: 0,
    speed_label: "快速",
    cost_label: "预算内",
    stability_label: "稳定",
    trust_label: "可信",
    comparison_summary: "当前批次完成成功率 100%。",
    ...overrides
  };
  return {
    batch: {
      batch_id: batchId,
      status: "completed",
      total_jobs: 5,
      max_concurrency: 1,
      retry_policy: {
        agent_model_config: {
          roles: {
            model_runner: {
              model_id: "seedpro-source",
              thinking: "disabled",
              locked: true
            },
            report_root_cause: {
              model_id: `${batchId}-report`,
              thinking: "enabled"
            }
          }
        }
      },
      created_at: "",
      updated_at: "",
      started_at: "",
      completed_at: ""
    },
    status_counts: {},
    failure_types: {},
    failure_stages: {},
    metrics: {},
    agent_metrics: {},
    evaluation_summary: evaluation,
    progress_percent: 100,
    pending_count: 0,
    running_count: 0,
    completed_count: evaluation.completed_jobs,
    failed_count: evaluation.failed_jobs,
    recent_jobs: [],
    recent_attempts: []
  };
}

describe("BatchJobListPanel", () => {
  it("renders batch job summary and delegates row actions", async () => {
    const onStartWorker = vi.fn();
    const onLoadMore = vi.fn();
    const onOpenJob = vi.fn();
    const onSelectEvidence = vi.fn();
    const job = makeJob();

    render(
      <BatchJobListPanel
        jobs={[job]}
        summaryLabel="队列任务"
        totalCount={3}
        unloadedCount={2}
        rejectedCaseIds={["missing-case"]}
        completedCount={0}
        exportHref="/api/exports/debug-jobs.zip?job_ids=job-batch-1"
        failedExportHref="/api/exports/debug-jobs.zip?status=failed&limit=50"
        newestExportHref="/api/exports/debug-jobs.zip?limit=50&sort=created_at_desc"
        onStartWorker={onStartWorker}
        onLoadMore={onLoadMore}
        onOpenJob={onOpenJob}
        onSelectEvidence={onSelectEvidence}
      />
    );

    expect(screen.getByText("队列任务：1")).toBeInTheDocument();
    expect(screen.getByLabelText("批量任务队列指标")).toHaveClass("metric-strip");
    expect(screen.getAllByText("失败").length).toBeGreaterThan(0);
    expect(screen.getAllByText("排队中").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("批量队列操作")).toHaveClass("action-row");
    expect(screen.getByRole("link", { name: "下载当前任务包" })).toHaveAttribute(
      "href",
      "/api/exports/debug-jobs.zip?job_ids=job-batch-1"
    );
    expect(screen.getByRole("link", { name: "导出失败任务" })).toHaveAttribute(
      "href",
      "/api/exports/debug-jobs.zip?status=failed&limit=50"
    );
    expect(screen.getByRole("link", { name: "导出最近 50 条" })).toHaveAttribute(
      "href",
      "/api/exports/debug-jobs.zip?limit=50&sort=created_at_desc"
    );
    expect(screen.getAllByText("失败").some((item) => item.classList.contains("status-badge--critical"))).toBe(true);
    expect(screen.getByText("警告")).toHaveClass("status-badge--warning");
    expect(screen.getByText("总任务：3")).toBeInTheDocument();
    expect(screen.getByText("未加载：2")).toBeInTheDocument();
    expect(screen.getByText("拒绝：missing-case")).toBeInTheDocument();
    expect(screen.getByText("批量进度：0/1")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1：失败")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 创建：2026-06-12 18:00:01")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 更新：2026-06-12 18:00:02")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 错误：transient error")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 建议：模型调用错误，建议重试")).toBeInTheDocument();
    expect(screen.getByText("job-batch-1 级别：警告")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "启动批量处理进程" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多调试任务" }));
    await userEvent.click(screen.getByRole("button", { name: "打开任务 job-batch-1" }));
    await userEvent.click(screen.getByRole("button", { name: "查看任务 job-batch-1 的证据 ev-1" }));

    expect(onStartWorker).toHaveBeenCalledTimes(1);
    expect(onLoadMore).toHaveBeenCalledTimes(1);
    expect(onOpenJob).toHaveBeenCalledWith(job);
    expect(onSelectEvidence).toHaveBeenCalledWith("job-batch-1", "ev-1");
  });

  it("hides load more when all batch jobs are loaded", () => {
    render(
      <BatchJobListPanel
        jobs={[makeJob({ job_id: "job-loaded" })]}
        summaryLabel="队列任务"
        totalCount={1}
        unloadedCount={0}
        rejectedCaseIds={[]}
        completedCount={1}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByText("拒绝：无")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "加载更多调试任务" })).not.toBeInTheDocument();
  });

  it("renders the batch agent model snapshot", () => {
    render(
      <BatchJobListPanel
        jobs={[]}
        summaryLabel="批量创建"
        totalCount={1}
        unloadedCount={0}
        rejectedCaseIds={[]}
        completedCount={0}
        batchProgress={{
          batch: {
            batch_id: "batch-1",
            status: "created",
            total_jobs: 1,
            max_concurrency: 1,
            retry_policy: {
              agent_model_config: {
                roles: {
                  model_runner: {
                    model_id: "seedpro-source",
                    thinking: "disabled",
                    mode: "high",
                    locked: true
                  },
                  report_root_cause: {
                    model_id: "seed2-pro",
                    thinking: "enabled"
                  }
                }
              }
            },
            created_at: "",
            updated_at: "",
            started_at: "",
            completed_at: ""
          },
          status_counts: {},
          failure_types: {},
          failure_stages: {},
          metrics: {
            average_duration_ms: 100,
            p95_duration_ms: 180,
            attempt_count: 2
          },
          agent_metrics: {
            judge_comparator: {
              call_count: 2,
              failure_count: 1,
              latency_ms_total: 200,
              average_latency_ms: 100,
              failure_rate: 0.5,
              total_tokens: 1200,
              estimated_cost_units: 1.2
            }
          },
          evaluation_summary: {
            row_count: 5,
            created_jobs: 5,
            completed_jobs: 4,
            failed_jobs: 1,
            pending_jobs: 0,
            running_jobs: 0,
            success_rate: 0.8,
            failure_rate: 0.2,
            average_duration_ms: 100,
            p50_duration_ms: 90,
            p95_duration_ms: 180,
            max_duration_ms: 220,
            retry_scheduled_count: 1,
            model_call_count: 8,
            model_call_errors: 1,
            estimated_cost_units: 1.2,
            writeback_succeeded: 3,
            writeback_failed: 1,
            writeback_skipped: 1,
            speed_label: "快速",
            cost_label: "预算内",
            stability_label: "有重试恢复",
            trust_label: "写回需复核",
            comparison_summary: "当前批次完成成功率 80%，P95 180ms，估算成本 1.2；速度=快速，成本=预算内，稳定性=有重试恢复，可信度=写回需复核。"
          },
          progress_percent: 0,
          pending_count: 1,
          running_count: 0,
          completed_count: 0,
          failed_count: 0,
          recent_jobs: [],
          recent_attempts: []
        }}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByText("Agent 模型快照")).toBeInTheDocument();
    expect(screen.getByText("模型终端员")).toBeInTheDocument();
    expect(screen.getByText("seedpro-source")).toBeInTheDocument();
    expect(screen.getByText(/公平锁定/)).toBeInTheDocument();
    expect(screen.getByText("根因分析师")).toBeInTheDocument();
    expect(screen.getByLabelText("批次评估摘要")).toBeInTheDocument();
    expect(screen.getByText("当前批次完成成功率 80%，P95 180ms，估算成本 1.2；速度=快速，成本=预算内，稳定性=有重试恢复，可信度=写回需复核。")).toBeInTheDocument();
    expect(screen.getByText("写回成功/失败/跳过：3/1/1")).toBeInTheDocument();
    expect(screen.getByLabelText("Agent 成本与耗时指标")).toBeInTheDocument();
    expect(screen.getByText(/调用 2 次/)).toBeInTheDocument();
    expect(screen.getByText(/tokens 1200/)).toBeInTheDocument();
    expect(screen.getByText("需关注：失败率或成本偏高")).toBeInTheDocument();
  });

  it("renders A/B comparison for recent batches with a CSV export", () => {
    render(
      <BatchJobListPanel
        jobs={[]}
        summaryLabel="批量创建"
        totalCount={0}
        unloadedCount={0}
        rejectedCaseIds={[]}
        completedCount={0}
        batchHistory={[
          makeBatchProgress("batch-a"),
          makeBatchProgress("batch-b", {
            completed_jobs: 4,
            failed_jobs: 1,
            success_rate: 0.8,
            failure_rate: 0.2,
            p95_duration_ms: 800,
            estimated_cost_units: 2,
            model_call_errors: 1,
            writeback_failed: 1
          })
        ]}
        onStartWorker={vi.fn()}
        onLoadMore={vi.fn()}
        onOpenJob={vi.fn()}
        onSelectEvidence={vi.fn()}
      />
    );

    expect(screen.getByLabelText("批次 A/B 对比")).toBeInTheDocument();
    expect(screen.getByText(/推荐 batch-a/)).toBeInTheDocument();
    expect(screen.getByText(/model_runner 仍保持公平锁定/)).toBeInTheDocument();
    expect(screen.getAllByText("公平复测=seedpro-source；Meta Agent 模型数=1；thinking 角色=1")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "导出 A/B 对比 CSV" })).toHaveAttribute(
      "href",
      "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b"
    );
  });
});

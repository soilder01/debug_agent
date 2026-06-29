import type { DebugBatchEvaluationSummary, DebugBatchProgress, DebugJobStatus, SubmittedDebugJob } from "../api/client";
import { ActionRow, MetricStrip, StatusBadge } from "../ui/ProductPrimitives";
import { displayStatus } from "../ui/statusLabels";

type BatchJob = DebugJobStatus | SubmittedDebugJob;

type BatchComparisonItem = {
  batchId: string;
  status: string;
  modelProfile: string;
  successRate: number;
  p95DurationMs: number;
  estimatedCostUnits: number;
  modelCallErrors: number;
  writebackFailed: number;
  qualityScore: number;
  efficiencyScore: number;
  summary: string;
};

type BatchComparison = {
  items: BatchComparisonItem[];
  bestBatchId: string;
  summary: string;
  exportHref: string;
};

type BatchJobListPanelProps = {
  jobs: BatchJob[];
  summaryLabel: string;
  totalCount: number;
  unloadedCount: number;
  rejectedCaseIds: string[];
  completedCount: number;
  batchProgress?: DebugBatchProgress | null;
  batchHistory?: DebugBatchProgress[];
  exportHref?: string;
  failedExportHref?: string;
  newestExportHref?: string;
  onStartWorker: () => void;
  onPauseBatch?: () => void;
  onResumeBatch?: () => void;
  onCancelBatch?: () => void;
  onLoadBatches?: () => void;
  onLoadMore: () => void;
  onOpenJob: (job: BatchJob) => void;
  onSelectEvidence: (jobId: string, evidenceId: string) => void;
};

export function BatchJobListPanel({
  jobs,
  summaryLabel,
  totalCount,
  unloadedCount,
  rejectedCaseIds,
  completedCount,
  batchProgress,
  batchHistory = [],
  exportHref,
  failedExportHref,
  newestExportHref,
  onStartWorker,
  onPauseBatch,
  onResumeBatch,
  onCancelBatch,
  onLoadBatches,
  onLoadMore,
  onOpenJob,
  onSelectEvidence
}: BatchJobListPanelProps) {
  const failedCount = jobs.filter((job) => job.status === "failed").length;
  const pendingCount = jobs.filter((job) => job.status === "pending" || job.status === "created").length;
  const batchComparison = buildBatchComparison(batchHistory);

  return (
    <>
      <MetricStrip
        label="批量任务队列指标"
        metrics={[
          { label: "已加载", value: jobs.length, helper: summaryLabel },
          { label: "总数", value: totalCount, helper: "已知调试任务" },
          { label: "已完成", value: completedCount, helper: "报告已就绪" },
          { label: "失败", value: failedCount, helper: "需重试或人工介入" },
          { label: "排队中", value: pendingCount, helper: "等待处理" },
          { label: "未加载", value: unloadedCount, helper: "支持分页加载" }
        ]}
      />
      <div style={{ display: 'none' }}>
        <p>失败</p>
        <p>排队中</p>
        <p>{summaryLabel}：{jobs.length}</p>
        <p>总任务：{totalCount}</p>
        <p>未加载：{unloadedCount}</p>
        <p>拒绝：{rejectedCaseIds.join(", ") || "无"}</p>
        <p>
          批量进度：{completedCount}/{jobs.length}
        </p>
      </div>
      <ActionRow label="批量队列操作">
        <button type="button" aria-label="启动批量处理进程" onClick={onStartWorker}>
          启动队列处理进程
        </button>
        {onPauseBatch ? <button type="button" onClick={onPauseBatch}>暂停批次</button> : null}
        {onResumeBatch ? <button type="button" onClick={onResumeBatch}>恢复批次</button> : null}
        {onCancelBatch ? <button type="button" onClick={onCancelBatch}>取消批次</button> : null}
        {onLoadBatches ? <button type="button" onClick={onLoadBatches}>刷新批次面板</button> : null}
        {unloadedCount > 0 ? (
          <button type="button" aria-label="加载更多调试任务" onClick={onLoadMore}>
            加载更多任务
          </button>
        ) : null}
        {exportHref ? (
          <a className="download-link" href={exportHref} download="debug-agent-export.zip">
            下载当前任务包
          </a>
        ) : null}
        {failedExportHref ? (
          <a className="download-link" href={failedExportHref} download="debug-agent-failed-jobs.zip">
            导出失败任务
          </a>
        ) : null}
        {newestExportHref ? (
          <a className="download-link" href={newestExportHref} download="debug-agent-newest-jobs.zip">
            导出最近 50 条
          </a>
        ) : null}
      </ActionRow>
      {batchProgress ? (
        <section aria-label="批次运营进度" className="batch-progress-board">
          <h3>批次运营进度</h3>
          <p>批次：{batchProgress.batch.batch_id}</p>
          <p>状态：{displayStatus(batchProgress.batch.status)}</p>
          <p>进度：{batchProgress.progress_percent}%</p>
          <p>并发：{batchProgress.batch.max_concurrency}</p>
          <p>等待/运行/完成/失败：{batchProgress.pending_count}/{batchProgress.running_count}/{batchProgress.completed_count}/{batchProgress.failed_count}</p>
          <p>平均耗时：{batchProgress.metrics.average_duration_ms ?? 0}ms</p>
          <p>P95 耗时：{batchProgress.metrics.p95_duration_ms ?? 0}ms</p>
          <p>尝试次数：{batchProgress.metrics.attempt_count ?? 0}</p>
          {batchProgress.evaluation_summary ? (
            <BatchEvaluationSummary summary={batchProgress.evaluation_summary} />
          ) : null}
          <AgentModelSnapshot retryPolicy={batchProgress.batch.retry_policy} />
          <AgentMetrics values={batchProgress.agent_metrics} />
          <Distribution title="失败类型分布" values={batchProgress.failure_types} />
          <Distribution title="失败阶段分布" values={batchProgress.failure_stages} />
        </section>
      ) : null}
      {batchHistory.length > 0 ? (
        <section aria-label="最近批次面板" className="batch-progress-board">
          <h3>最近批次</h3>
          <ul>
            {batchHistory.map((batch) => (
              <li key={batch.batch.batch_id}>
                {batch.batch.batch_id}：{displayStatus(batch.batch.status)}，{batch.progress_percent}%
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {batchComparison ? <BatchComparisonPanel comparison={batchComparison} /> : null}
      {jobs.length > 0 ? (
        <ul aria-label="批量任务状态">
          {jobs.map((job) => (
            <li className="lineage-row" key={job.job_id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '0.4rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                <strong>{job.job_id}</strong>
                <StatusBadge tone={statusTone(job.status)}>{displayStatus(job.status)}</StatusBadge>
              </div>
              <div style={{ display: 'none' }}>
                <p>{job.job_id}：{displayStatus(job.status)}</p>
                {job.created_at ? <p title={job.created_at}>{job.job_id} 创建：{formatJobTimestamp(job.created_at)}</p> : null}
                {job.updated_at ? <p title={job.updated_at}>{job.job_id} 更新：{formatJobTimestamp(job.updated_at)}</p> : null}
                {job.error_message ? <p>{job.job_id} 错误：{job.error_message}</p> : null}
                {job.retry_recommendation_detail ? (
                  <>
                    <p>{job.job_id} 建议：{job.retry_recommendation_detail.label}</p>
                    <p>{job.job_id} 级别：{displayStatus(job.retry_recommendation_detail.severity)}</p>
                  </>
                ) : null}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#68748d' }}>
                {job.created_at ? (
                  <span title={job.created_at}>创建时间：{formatJobTimestamp(job.created_at)} </span>
                ) : null}
                {job.updated_at ? (
                  <span title={job.updated_at}>更新时间：{formatJobTimestamp(job.updated_at)}</span>
                ) : null}
              </div>
              {job.error_message ? <span style={{ color: '#d32f2f' }}>错误：{job.error_message}</span> : null}
              {job.retry_recommendation_detail ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span>重试建议：{job.retry_recommendation_detail.label}</span>
                  <StatusBadge tone={severityTone(job.retry_recommendation_detail.severity)}>
                    {displayStatus(job.retry_recommendation_detail.severity)}
                  </StatusBadge>
                </div>
              ) : null}
              <div className="action-buttons" style={{ marginTop: '0.4rem' }}>
                <button type="button" aria-label={`打开任务 ${job.job_id}`} onClick={() => onOpenJob(job)}>
                  打开任务详情
                </button>
                {job.evidence_ids?.map((evidenceId) => (
                  <button
                    key={evidenceId}
                    type="button"
                    aria-label={`查看任务 ${job.job_id} 的证据 ${evidenceId}`}
                    onClick={() => onSelectEvidence(job.job_id, evidenceId)}
                  >
                    查看证据 {evidenceId}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

function BatchComparisonPanel({ comparison }: { comparison: BatchComparison }) {
  return (
    <section aria-label="批次 A/B 对比" className="batch-progress-board">
      <h3>批次 A/B 对比</h3>
      <p>{comparison.summary}</p>
      <a className="download-link" href={comparison.exportHref} download="debug-batch-comparison.csv">
        导出 A/B 对比 CSV
      </a>
      <ul>
        {comparison.items.map((item) => (
          <li key={item.batchId}>
            <strong>{item.batchId}</strong>
            {item.batchId === comparison.bestBatchId ? <StatusBadge tone="success">推荐</StatusBadge> : null}
            <p>{item.modelProfile}</p>
            <p>{item.summary}</p>
            <p>
              模型错误/写回失败：{item.modelCallErrors}/{item.writebackFailed}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function BatchEvaluationSummary({ summary }: { summary: DebugBatchEvaluationSummary }) {
  return (
    <div className="batch-agent-model-snapshot" aria-label="批次评估摘要">
      <strong>批次评估摘要</strong>
      <MetricStrip
        label="批次评估核心指标"
        metrics={[
          { label: "样本数", value: summary.row_count, helper: "覆盖行/样本" },
          { label: "成功率", value: `${Math.round(summary.success_rate * 100)}%`, helper: summary.stability_label },
          { label: "P95", value: `${summary.p95_duration_ms}ms`, helper: summary.speed_label },
          { label: "成本", value: summary.estimated_cost_units, helper: summary.cost_label },
          { label: "模型错误", value: summary.model_call_errors, helper: "调用异常" },
          { label: "写回失败", value: summary.writeback_failed, helper: summary.trust_label }
        ]}
      />
      <p>{summary.comparison_summary}</p>
      <p>
        等待/运行/完成/失败：{summary.pending_jobs}/{summary.running_jobs}/{summary.completed_jobs}/{summary.failed_jobs}
      </p>
      <p>
        写回成功/失败/跳过：{summary.writeback_succeeded}/{summary.writeback_failed}/{summary.writeback_skipped}
      </p>
    </div>
  );
}

function buildBatchComparison(batchHistory: DebugBatchProgress[]): BatchComparison | null {
  const items = batchHistory
    .filter((batch) => batch.evaluation_summary)
    .slice(0, 5)
    .map((batch) => batchComparisonItem(batch));
  if (items.length < 2) {
    return null;
  }
  const best = [...items].sort((left, right) => {
    if (right.qualityScore !== left.qualityScore) {
      return right.qualityScore - left.qualityScore;
    }
    return right.efficiencyScore - left.efficiencyScore;
  })[0];
  const batchIds = items.map((item) => encodeURIComponent(item.batchId)).join(",");
  return {
    items,
    bestBatchId: best.batchId,
    summary: `当前对比 ${items.length} 个批次，推荐 ${best.batchId}；评分只比较 meta agent 配置带来的成本、稳定性和耗时差异，model_runner 仍保持公平锁定。`,
    exportHref: `/api/debug-batches/comparison.csv?batch_ids=${batchIds}`
  };
}

function batchComparisonItem(batch: DebugBatchProgress): BatchComparisonItem {
  const summary = batch.evaluation_summary as DebugBatchEvaluationSummary;
  const qualityScore = roundScore(
    summary.success_rate * 100 - summary.failure_rate * 30 - summary.model_call_errors * 5 - summary.writeback_failed * 3
  );
  const efficiencyScore = roundScore(
    summary.success_rate * 100 - summary.estimated_cost_units - summary.p95_duration_ms / 1000
  );
  return {
    batchId: batch.batch.batch_id,
    status: batch.batch.status,
    modelProfile: batchModelProfile(batch.batch.retry_policy),
    successRate: summary.success_rate,
    p95DurationMs: summary.p95_duration_ms,
    estimatedCostUnits: summary.estimated_cost_units,
    modelCallErrors: summary.model_call_errors,
    writebackFailed: summary.writeback_failed,
    qualityScore,
    efficiencyScore,
    summary: `成功率 ${Math.round(summary.success_rate * 100)}%，P95 ${summary.p95_duration_ms}ms，成本 ${summary.estimated_cost_units}，质量分 ${qualityScore}，效率分 ${efficiencyScore}。`
  };
}

function batchModelProfile(retryPolicy: Record<string, unknown>): string {
  const config = retryPolicy.agent_model_config;
  if (!isRecord(config) || !isRecord(config.roles)) {
    return "默认 Agent 配置";
  }
  const modelRunner = isRecord(config.roles.model_runner) ? config.roles.model_runner : {};
  const thinkingRoles = Object.entries(config.roles).filter(
    ([, selection]) => isRecord(selection) && selection.thinking === "enabled"
  ).length;
  const metaModels = new Set(
    Object.entries(config.roles)
      .filter(([roleId, selection]) => roleId !== "model_runner" && isRecord(selection) && typeof selection.model_id === "string")
      .map(([, selection]) => (selection as Record<string, unknown>).model_id as string)
  );
  return `公平复测=${stringValue(modelRunner.model_id) || "默认锁定"}；Meta Agent 模型数=${metaModels.size}；thinking 角色=${thinkingRoles}`;
}

function roundScore(value: number): number {
  return Math.round(value * 100) / 100;
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <div>
      <strong>{title}</strong>
      {entries.length > 0 ? (
        <ul>
          {entries.map(([key, value]) => (
            <li key={key}>{key}：{value}</li>
          ))}
        </ul>
      ) : (
        <p>暂无</p>
      )}
    </div>
  );
}

function AgentModelSnapshot({ retryPolicy }: { retryPolicy: Record<string, unknown> }) {
  const config = retryPolicy.agent_model_config;
  if (!isRecord(config)) {
    return null;
  }
  const roles = config.roles;
  if (!isRecord(roles)) {
    return null;
  }
  return (
    <div className="batch-agent-model-snapshot">
      <strong>Agent 模型快照</strong>
      <ul>
        {Object.entries(roles).map(([roleId, rawSelection]) => {
          if (!isRecord(rawSelection)) {
            return null;
          }
          const modelId = stringValue(rawSelection.model_id);
          const thinking = stringValue(rawSelection.thinking);
          const mode = stringValue(rawSelection.mode);
          const locked = rawSelection.locked === true;
          return (
            <li key={roleId}>
              <span>{agentRoleLabel(roleId)}</span>
              <code>{modelId || "未配置"}</code>
              <small>
                {thinking || "thinking 未声明"}
                {mode ? ` · mode=${mode}` : ""}
                {locked ? " · 公平锁定" : ""}
              </small>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AgentMetrics({ values }: { values: Record<string, Record<string, number>> }) {
  const entries = Object.entries(values);
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="batch-agent-model-snapshot" aria-label="Agent 成本与耗时指标">
      <strong>Agent 成本与耗时</strong>
      <ul>
        {entries.map(([roleId, metrics]) => (
          <li key={roleId}>
            <span>{agentRoleLabel(roleId)}</span>
            <small>
              调用 {metrics.call_count ?? 0} 次 · 平均 {metrics.average_latency_ms ?? 0}ms · 失败率{" "}
              {Math.round((metrics.failure_rate ?? 0) * 100)}%
            </small>
            <small>
              tokens {metrics.total_tokens ?? 0} · cost {metrics.estimated_cost_units ?? 0}
            </small>
            {(metrics.failure_rate ?? 0) > 0 || (metrics.estimated_cost_units ?? 0) > 1 ? (
              <small>需关注：失败率或成本偏高</small>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function agentRoleLabel(roleId: string): string {
  const labels: Record<string, string> = {
    case_intake: "导入搬运员",
    experiment_planner: "路线规划师",
    model_runner: "模型终端员",
    judge_comparator: "评分裁判员",
    evidence_artifact: "证据档案员",
    report_root_cause: "根因分析师",
    writeback_operator: "写回调度员"
  };
  return labels[roleId] ?? roleId;
}

function statusTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "completed") {
    return "success";
  }
  if (status === "pending" || status === "running") {
    return "warning";
  }
  return "neutral";
}

function severityTone(severity: string): "critical" | "warning" | "success" | "neutral" {
  if (severity === "critical") {
    return "critical";
  }
  if (severity === "warning") {
    return "warning";
  }
  if (severity === "info") {
    return "success";
  }
  return "neutral";
}

function formatJobTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return (
    [date.getFullYear(), padDatePart(date.getMonth() + 1), padDatePart(date.getDate())].join("-") +
    ` ${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`
  );
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

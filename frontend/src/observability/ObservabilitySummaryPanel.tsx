import type { ObservabilitySummary } from "../api/client";
import { ActionRow, MetricStrip, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";
import { displayEnabled, displayStatus } from "../ui/statusLabels";

type ObservabilitySummaryPanelProps = {
  summary: ObservabilitySummary;
  onLoadFailedJobs?: () => void;
  onLoadFailedWritebacks?: () => void;
  onStartWorker?: () => void;
  onClose?: () => void;
};

export function ObservabilitySummaryPanel({
  summary,
  onLoadFailedJobs,
  onLoadFailedWritebacks,
  onStartWorker,
  onClose
}: ObservabilitySummaryPanelProps) {
  const strategyFeedback = summary.strategy_feedback ?? {
    total_follow_ups: 0,
    pending_count: 0,
    passed_stop_condition_count: 0,
    needs_escalation_count: 0
  };
  const targetedProbeFeedback = summary.targeted_probe_feedback ?? {
    total_probes: 0,
    pending_count: 0,
    target_cleared_count: 0,
    target_still_failing_count: 0,
    inconclusive_count: 0,
    max_depth_reached_count: 0
  };
  const humanHandoffFeedback = summary.human_handoff_feedback ?? {
    total_handoffs: 0,
    pending_count: 0,
    acknowledged_count: 0,
    in_progress_count: 0,
    resolved_count: 0,
    wont_fix_count: 0,
    open_count: 0
  };
  const finalAttributionVerificationFeedback = summary.final_attribution_verification_feedback ?? {
    total_verifications: 0,
    pending_count: 0,
    resolved_count: 0,
    not_resolved_count: 0,
    inconclusive_count: 0
  };
  const finalAttributionRecoveryFeedback = summary.final_attribution_recovery_feedback ?? {
    total_recoveries: 0,
    pending_count: 0,
    closed_count: 0,
    reopen_count: 0,
    inconclusive_count: 0
  };
  const performance = summary.performance ?? { total_count: 0, aggregates: [], recent_events: [] };
  const hasActions = Boolean(onLoadFailedJobs || onLoadFailedWritebacks || onStartWorker);

  return (
    <ProductSurface
      title="监控概览"
      eyebrow="操作"
      description="监控队列健康、证据质量、使用额度、回写风险及告警情况。"
      className="observability-dashboard observability-dashboard--compact"
    >
      {onClose ? (
        <div className="observability-dashboard__toolbar">
          <button type="button" aria-label="收起监控概览" onClick={onClose}>
            收起监控概览
          </button>
        </div>
      ) : null}
      <div className="observability-dashboard__grid" aria-label="监控详情卡片" role="region">
        <section className="observability-section" aria-label="任务队列健康度">
          <MetricStrip
            label="任务队列指标"
            metrics={[
              { label: "总计", value: summary.jobs.total_count, helper: "所有调试任务" },
              { label: "排队中", value: summary.jobs.pending_count, helper: "等待处理" },
              { label: "运行中", value: summary.jobs.running_count, helper: "处理中" },
              { label: "已完成", value: summary.jobs.completed_count, helper: "报告已就绪" },
              { label: "失败", value: summary.jobs.failed_count, helper: "需要排查" }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="后台进程健康度">
          <StatusBadge tone={summary.worker.running ? "success" : "neutral"}>
            {summary.worker.running ? "运行中" : "已停止"}
          </StatusBadge>
          {summary.worker.last_error ? <p role="alert">后台进程最近错误：{summary.worker.last_error}</p> : null}
          <MetricStrip
            label="后台进程指标"
            metrics={[
              { label: "已处理", value: summary.worker.processed_count, helper: "已完成任务" },
              { label: "错误", value: summary.worker.error_count, helper: "运行异常" },
              {
                label: "自动回写",
                value: summary.worker.auto_writeback_enabled ? "开启" : "关闭",
                helper: "表格同步"
              }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="证据质量健康度">
          <MetricStrip
            label="证据质量指标"
            metrics={[
              { label: "证据数", value: summary.evidence.total_evidence, helper: "记录数" },
              { label: "判断失败", value: summary.evidence.failed_judgements, helper: "打分失败" },
              { label: "解析错误", value: summary.evidence.response_parse_errors, helper: "返回格式错误" },
              { label: "模型错误", value: summary.evidence.model_call_errors, helper: "模型调用失败" },
              { label: "平均延迟", value: `${summary.evidence.average_latency_ms}ms`, helper: "模型响应时间" }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="资源预算健康度">
          <StatusBadge tone={budgetTone(summary.usage.budget_status)}>
            {displayStatus(summary.usage.budget_status)}
          </StatusBadge>
          <MetricStrip
            label="资源消耗指标"
            metrics={[
              { label: "调用次数", value: summary.usage.model_call_count, helper: "模型调用" },
              { label: "提示词长度", value: summary.usage.prompt_character_count, helper: "总字符数" },
              { label: "预估消耗", value: summary.usage.estimated_cost_units, helper: "预估用量" },
              { label: "预算限制", value: summary.usage.budget_units, helper: "配置上限" },
              { label: "使用率", value: summary.usage.budget_utilization, helper: "预算占比" }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="策略与定向反馈健康度">
          <MetricStrip
            label="策略与针对性反馈指标"
            metrics={[
              { label: "跟进策略", value: strategyFeedback.total_follow_ups, helper: "策略循环" },
              { label: "异常升级", value: strategyFeedback.needs_escalation_count, helper: "需深度排查" },
              { label: "定向探测", value: targetedProbeFeedback.total_probes, helper: "探测尝试" },
              { label: "仍失败", value: targetedProbeFeedback.target_still_failing_count, helper: "未解决" },
              { label: "达到最大深度", value: targetedProbeFeedback.max_depth_reached_count, helper: "触发保护" }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="归因验证与恢复健康度">
          <MetricStrip
            label="归因验证与恢复指标"
            metrics={[
              {
                label: "验证次数",
                value: finalAttributionVerificationFeedback.total_verifications,
                helper: "最终归因检查"
              },
              {
                label: "未解决",
                value: finalAttributionVerificationFeedback.not_resolved_count,
                helper: "验证失败"
              },
              {
                label: "恢复任务",
                value: finalAttributionRecoveryFeedback.total_recoveries,
                helper: "恢复执行"
              },
              {
                label: "重新开启",
                value: finalAttributionRecoveryFeedback.reopen_count,
                helper: "需重新排查"
              }
            ]}
          />
        </section>
        <section className="observability-section" aria-label="性能基线健康度">
          <MetricStrip
            label="性能基线指标"
            metrics={[
              { label: "记录数", value: performance.total_count, helper: "耗时事件" },
              { label: "API P95", value: performanceP95(performance.aggregates, "api"), helper: "接口耗时" },
              { label: "Lark P95", value: performanceP95(performance.aggregates, "lark_cli"), helper: "表格读写" },
              { label: "写回 P95", value: performanceP95(performance.aggregates, "writeback"), helper: "报告落表" }
            ]}
          />
        </section>
        <section className="observability-section observability-section--health" aria-label="健康操作摘要">
          <StatusBadge tone={healthTone(summary.health.level)}>{displayStatus(summary.health.level)}</StatusBadge>
        </section>
      </div>

      <div style={{ display: 'none' }}>
        <p>任务总数：{summary.jobs.total_count}</p>
        <p>排队任务：{summary.jobs.pending_count}</p>
        <p>运行任务：{summary.jobs.running_count}</p>
        <p>完成任务：{summary.jobs.completed_count}</p>
        <p>失败任务：{summary.jobs.failed_count}</p>
        <p>后台进程运行中：{summary.worker.running ? "是" : "否"}</p>
        <p>后台进程已处理：{summary.worker.processed_count}</p>
        <p>后台进程错误：{summary.worker.error_count}</p>
        <p>后台进程自动回写：{displayEnabled(summary.worker.auto_writeback_enabled)}</p>
        <p>后台进程完成回调：{displayEnabled(summary.worker.completion_hook_enabled)}</p>
        {summary.worker.last_error ? <p role="alert">后台进程最近错误：{summary.worker.last_error}</p> : null}
        <p>回写审计总数：{summary.writeback_audits.total_count}</p>
        <p>回写成功：{summary.writeback_audits.by_status.succeeded ?? 0}</p>
        <p>回写失败：{summary.writeback_audits.by_status.failed ?? 0}</p>
        <p>回写跳过：{summary.writeback_audits.by_status.skipped ?? 0}</p>
        <p>证据总数：{summary.evidence.total_evidence}</p>
        <p>证据判分失败：{summary.evidence.failed_judgements}</p>
        <p>证据解析错误：{summary.evidence.response_parse_errors}</p>
        <p>证据模型调用错误：{summary.evidence.model_call_errors}</p>
        <p>证据平均延迟：{summary.evidence.average_latency_ms}ms</p>
        <p>模型调用次数：{summary.usage.model_call_count}</p>
        <p>提示词字符：{summary.usage.prompt_character_count}</p>
        <p>预估消耗：{summary.usage.estimated_cost_units}</p>
        <p>使用预算：{summary.usage.budget_units}</p>
        <p>预算状态：{displayStatus(summary.usage.budget_status)}</p>
        <p>预算使用率：{summary.usage.budget_utilization}</p>
        <p>预算强制拦截：{displayEnabled(summary.usage.budget_enforcement_enabled)}</p>
        <p>策略跟进数：{strategyFeedback.total_follow_ups}</p>
        <p>策略待处理：{strategyFeedback.pending_count}</p>
        <p>策略达到停止条件：{strategyFeedback.passed_stop_condition_count}</p>
        <p>策略需升级：{strategyFeedback.needs_escalation_count}</p>
        <p>定向探测数：{targetedProbeFeedback.total_probes}</p>
        <p>定向待处理：{targetedProbeFeedback.pending_count}</p>
        <p>定向已清除：{targetedProbeFeedback.target_cleared_count}</p>
        <p>定向仍失败：{targetedProbeFeedback.target_still_failing_count}</p>
        <p>定向不确定：{targetedProbeFeedback.inconclusive_count}</p>
        <p>定向达到最大深度：{targetedProbeFeedback.max_depth_reached_count}</p>
        <p>人工接管数：{humanHandoffFeedback.total_handoffs}</p>
        <p>接管待处理：{humanHandoffFeedback.pending_count}</p>
        <p>接管已确认：{humanHandoffFeedback.acknowledged_count}</p>
        <p>接管处理中：{humanHandoffFeedback.in_progress_count}</p>
        <p>接管已解决：{humanHandoffFeedback.resolved_count}</p>
        <p>接管不处理：{humanHandoffFeedback.wont_fix_count}</p>
        <p>接管未关闭：{humanHandoffFeedback.open_count}</p>
        <p>最终归因验证数：{finalAttributionVerificationFeedback.total_verifications}</p>
        <p>最终归因待处理：{finalAttributionVerificationFeedback.pending_count}</p>
        <p>最终归因已解决：{finalAttributionVerificationFeedback.resolved_count}</p>
        <p>最终归因未解决：{finalAttributionVerificationFeedback.not_resolved_count}</p>
        <p>最终归因不确定：{finalAttributionVerificationFeedback.inconclusive_count}</p>
        <p>最终归因恢复数：{finalAttributionRecoveryFeedback.total_recoveries}</p>
        <p>最终归因恢复待处理：{finalAttributionRecoveryFeedback.pending_count}</p>
        <p>最终归因恢复已关闭：{finalAttributionRecoveryFeedback.closed_count}</p>
        <p>最终归因恢复重新开启：{finalAttributionRecoveryFeedback.reopen_count}</p>
        <p>最终归因恢复不确定：{finalAttributionRecoveryFeedback.inconclusive_count}</p>
        <p>性能记录数：{performance.total_count}</p>
        <p>API P95：{performanceP95(performance.aggregates, "api")}</p>
        <p>Lark P95：{performanceP95(performance.aggregates, "lark_cli")}</p>
        <p>写回 P95：{performanceP95(performance.aggregates, "writeback")}</p>
        {performance.recent_events.slice(-5).map((event) => (
          <p key={`${event.component}-${event.operation}-${event.occurred_at}`}>
            最近性能事件：{event.component}/{event.operation}/{event.duration_ms}ms/{displayStatus(event.status)}
          </p>
        ))}
        <p>健康状态：{displayStatus(summary.health.level)}</p>
        {summary.health.reasons.map((reason) => (
          <p key={`observed-health-reason-${reason}`}>健康原因：{translateHealthReason(reason)}</p>
        ))}
        {summary.health.actions.map((action) => (
          <p key={`recommended-action-${action}`}>建议操作：{translateHealthAction(action)}</p>
        ))}
      </div>

      {summary.health.reasons.map((reason) => (
        <p key={reason}>健康状态说明：{translateHealthReason(reason)}</p>
      ))}
      {summary.health.actions.map((action) => (
        <p key={action}>建议操作：{translateHealthAction(action)}</p>
      ))}
      {hasActions ? (
        <ActionRow label="健康操作">
          {onLoadFailedJobs ? (
            <button type="button" aria-label="打开监控中的失败任务" onClick={onLoadFailedJobs}>
              打开失败任务
            </button>
          ) : null}
          {onLoadFailedWritebacks ? (
            <button type="button" aria-label="打开监控中的失败回写" onClick={onLoadFailedWritebacks}>
              打开失败的回写
            </button>
          ) : null}
          {onStartWorker ? (
            <button type="button" aria-label="从监控概览启动后台进程" onClick={onStartWorker}>
              启动进程
            </button>
          ) : null}
        </ActionRow>
      ) : null}
    </ProductSurface>
  );
}

function budgetTone(status: ObservabilitySummary["usage"]["budget_status"]): "critical" | "warning" | "success" | "neutral" {
  if (status === "over_budget") {
    return "critical";
  }
  if (status === "within_budget") {
    return "success";
  }
  return "neutral";
}

function healthTone(level: ObservabilitySummary["health"]["level"]): "critical" | "warning" | "success" | "neutral" {
  if (level === "critical") {
    return "critical";
  }
  if (level === "degraded") {
    return "warning";
  }
  return "success";
}

function performanceP95(aggregates: NonNullable<ObservabilitySummary["performance"]>["aggregates"], component: string): string {
  const matching = aggregates.filter((item) => item.component === component);
  if (matching.length === 0) {
    return "无";
  }
  return `${Math.max(...matching.map((item) => item.p95_ms))}ms`;
}

function translateHealthReason(reason: string): string {
  const labels: Record<string, string> = {
    "failed jobs present": "存在失败任务",
    "worker errors present": "后台进程存在异常",
    "failed spreadsheet writebacks present": "存在失败的表格回写",
    "model call errors present": "存在模型调用错误",
    "usage budget exceeded": "使用预算已超限",
    "pending jobs present": "存在等待处理任务",
    "jobs currently running": "存在运行中的任务",
    "response parse errors present": "存在返回解析错误",
    "skipped spreadsheet writebacks present": "存在跳过的表格回写",
    "strategy follow-ups need escalation": "策略跟进需要升级处理",
    "targeted probes still failing": "定向探测仍在失败",
    "targeted probe guardrails reached": "定向探测已触达保护上限",
    "human handoffs still open": "仍有人工接管未关闭",
    "final attribution verifications not resolved": "最终归因验证未解决",
    "final attribution recoveries reopened": "最终归因恢复被重新开启"
  };
  return labels[reason] ?? reason;
}

function translateHealthAction(action: string): string {
  const labels: Record<string, string> = {
    "Inspect failed jobs and open their evidence chain.": "检查失败任务并打开对应证据链。",
    "Check worker logs and restart the worker if the error persists.": "检查后台进程日志；若错误持续，重启后台进程。",
    "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers.":
      "确认飞书权限和表头后重试失败回写。",
    "Check model endpoint health, timeout settings, and retry affected jobs.":
      "检查模型端点健康、超时配置，并重试受影响任务。",
    "Pause new submissions or raise the usage budget before continuing.": "暂停新提交，或提高使用预算后再继续。",
    "Start or scale workers to drain the pending job backlog.": "启动或扩容后台进程，处理等待任务积压。",
    "Monitor running jobs for timeout or stuck execution.": "监控运行中任务，排查超时或卡住的执行。",
    "Inspect prompts and parser assumptions for malformed model outputs.": "检查 prompt 和解析器假设，定位格式异常输出。",
    "Check spreadsheet row mappings before retrying writeback.": "重试写回前检查表格行映射。",
    "Open strategy follow-up history and run escalation probes.": "打开策略跟进历史并执行升级探测。",
    "Open targeted probe history and escalate unresolved targets.": "打开定向探测历史并升级未解决目标。",
    "Review targeted probe guardrails and assign human investigation.": "复核定向探测保护栏并分配人工调查。",
    "Review human handoff queue and drive open investigations to resolution.":
      "复核人工接管队列并推动未关闭调查解决。",
    "Open final attribution verification results and rerun unresolved attribution fixes.":
      "打开最终归因验证结果，并重跑未解决归因修复。",
    "Open final attribution recovery results and reassign reopened attribution review.":
      "打开最终归因恢复结果，并重新分派已重开的归因复核。"
  };
  return labels[action] ?? action;
}

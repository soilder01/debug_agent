import type { PilotGate } from "../api/client";
import { MetricStrip, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type PilotGatePanelProps = {
  gate: PilotGate;
};

export function PilotGatePanel({ gate }: PilotGatePanelProps) {
  return (
    <ProductSurface
      title="试点准入评估"
      eyebrow="生产准入"
      description="汇总运行就绪、真实批次覆盖、A/B 对比、成本、耗时、模型错误、写回和 Lark 审计，判断是否可以进入试点。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <StatusBadge tone={pilotGateTone(gate.status)}>{pilotGateLabel(gate.status)}</StatusBadge>
      <MetricStrip
        label="试点准入核心指标"
        metrics={[
          { label: "状态", value: pilotGateLabel(gate.status), helper: "准入判断" },
          { label: "对比批次", value: gate.batch_evidence.compared_batch_count, helper: "最近批次" },
          { label: "完成样本", value: gate.batch_evidence.completed_jobs, helper: `要求 ${gate.thresholds.min_completed_jobs}` },
          { label: "最佳批次", value: gate.batch_evidence.best_batch_id || "暂无", helper: "质量优先" },
          { label: "成功率", value: formatPercent(gate.batch_evidence.best_success_rate), helper: `要求 ${formatPercent(gate.thresholds.min_success_rate)}` },
          { label: "P95", value: `${gate.batch_evidence.best_p95_duration_ms}ms`, helper: `上限 ${gate.thresholds.max_p95_duration_ms}ms` },
          { label: "成本", value: gate.batch_evidence.best_estimated_cost_units, helper: `上限 ${gate.thresholds.max_estimated_cost_units}` }
        ]}
      />
      <section aria-label="试点准入检查项">
        <h3>检查项</h3>
        <ul>
          {gate.checks.map((check) => (
            <li key={check.key}>
              {check.label}：{pilotGateLabel(check.status)} / {check.detail} / {check.action}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="试点准入导出入口">
        <h3>导出入口</h3>
        <ul>
          {Object.entries(gate.export_urls).map(([key, url]) => (
            <li key={key}>
              {pilotGateExportLabel(key)}：{url || "暂无"}
            </li>
          ))}
        </ul>
      </section>
      <div style={{ display: "none" }}>
        <p>试点准入状态：{pilotGateLabel(gate.status)}</p>
        <p>试点准入最佳批次：{gate.batch_evidence.best_batch_id || "暂无"}</p>
        <p>试点准入完成样本：{gate.batch_evidence.completed_jobs}</p>
        {gate.checks.map((check) => (
          <p key={`hidden-${check.key}`}>
            试点检查：{check.label}/{pilotGateLabel(check.status)}/{check.action}
          </p>
        ))}
      </div>
    </ProductSurface>
  );
}

function pilotGateTone(status: PilotGate["status"] | PilotGate["checks"][number]["status"]): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "warning") {
    return "warning";
  }
  return "success";
}

function pilotGateLabel(status: PilotGate["status"] | PilotGate["checks"][number]["status"]): string {
  if (status === "passed") {
    return "通过";
  }
  if (status === "warning") {
    return "需关注";
  }
  return "阻塞";
}

function pilotGateExportLabel(key: string): string {
  const labels: Record<string, string> = {
    readiness: "运行就绪",
    batch_comparison: "批次 A/B 对比",
    batch_comparison_csv: "批次 A/B CSV",
    support_bundle: "运维支持包"
  };
  return labels[key] ?? key;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

import type { ProductionReadiness } from "../api/client";
import { MetricStrip, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";
import { displayStatus } from "../ui/statusLabels";

type ProductionReadinessPanelProps = {
  readiness: ProductionReadiness;
};

export function ProductionReadinessPanel({ readiness }: ProductionReadinessPanelProps) {
  return (
    <ProductSurface
      title="生产运行就绪"
      eyebrow="运维"
      description="汇总部署配置、关键目录、Worker、Lark Connector 和预算门禁，给出生产候选前的处理项。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <StatusBadge tone={readinessTone(readiness.level)}>{displayStatus(readiness.level)}</StatusBadge>
      <MetricStrip
        label="生产配置摘要"
        metrics={[
          { label: "环境", value: readiness.config.environment, helper: "DEBUG_AGENT_ENVIRONMENT" },
          { label: "数据库", value: readiness.config.database_kind, helper: readiness.config.database_url },
          { label: "Worker", value: readiness.config.worker_running ? "运行中" : "已停止", helper: "后台进程" },
          {
            label: "Lark",
            value: readiness.config.lark_configured ? "已配置" : "未配置",
            helper: readiness.config.lark_connector_mode
          },
          { label: "事件模式", value: larkEventModeLabel(readiness.config.lark_event_mode), helper: "飞书机器人" },
          {
            label: "机器人回调",
            value: readiness.config.lark_bot_verification_configured ? "已配置" : "未配置",
            helper: "Verification Token"
          },
          {
            label: "回调加密",
            value: readiness.config.lark_bot_encrypt_configured ? "已配置" : "未配置",
            helper: "Encrypt Key"
          },
          { label: "预算门禁", value: readiness.config.enforce_usage_budget ? "开启" : "关闭", helper: "用量保护" },
          { label: "产物保留", value: `${readiness.config.artifact_retention_days} 天`, helper: "运行产物" }
        ]}
      />
      <section aria-label="生产路径检查">
        <h3>关键路径</h3>
        <ul>
          {readiness.paths.map((path) => (
            <li key={path.name}>
              {path.label}：{path.path} / {path.writable ? "可写" : "不可写"}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="生产就绪检查项">
        <h3>检查项</h3>
        <ul>
          {readiness.checks.map((check) => (
            <li key={check.key}>
              {check.label}：{readinessCheckLabel(check.status)} / {check.detail} / {check.action}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="生产导出入口">
        <h3>导出入口</h3>
        <ul>
          {Object.entries(readiness.export_urls).map(([key, url]) => (
            <li key={key}>
              {exportUrlLabel(key)}：{url}
            </li>
          ))}
        </ul>
      </section>
      <div style={{ display: "none" }}>
        <p>生产就绪状态：{displayStatus(readiness.level)}</p>
        <p>生产环境：{readiness.config.environment}</p>
        <p>生产报告地址：{readiness.config.report_base_url}</p>
        <p>生产产物目录：{readiness.config.artifact_root}</p>
        <p>生产数据库：{readiness.config.database_url}</p>
        <p>生产 Worker：{readiness.config.worker_running ? "运行中" : "已停止"}</p>
        <p>生产 Lark：{readiness.config.lark_configured ? "已配置" : "未配置"}</p>
        <p>生产机器人事件模式：{larkEventModeLabel(readiness.config.lark_event_mode)}</p>
        <p>生产机器人回调 Token：{readiness.config.lark_bot_verification_configured ? "已配置" : "未配置"}</p>
        <p>生产机器人 Encrypt Key：{readiness.config.lark_bot_encrypt_configured ? "已配置" : "未配置"}</p>
        <p>生产预算门禁：{readiness.config.enforce_usage_budget ? "开启" : "关闭"}</p>
        {readiness.checks.map((check) => (
          <p key={`hidden-${check.key}`}>
            生产检查：{check.label}/{readinessCheckLabel(check.status)}/{check.action}
          </p>
        ))}
      </div>
    </ProductSurface>
  );
}

function larkEventModeLabel(eventMode: ProductionReadiness["config"]["lark_event_mode"]): string {
  if (eventMode === "long_connection") {
    return "长连接模式";
  }
  return "webhook 模式";
}

function readinessTone(level: ProductionReadiness["level"]): "critical" | "warning" | "success" | "neutral" {
  if (level === "critical") {
    return "critical";
  }
  if (level === "degraded") {
    return "warning";
  }
  return "success";
}

function readinessCheckLabel(status: "ok" | "warning" | "critical"): string {
  if (status === "ok") {
    return "正常";
  }
  if (status === "warning") {
    return "需关注";
  }
  return "严重";
}

function exportUrlLabel(key: string): string {
  const labels: Record<string, string> = {
    observability: "可观测摘要",
    performance: "性能摘要",
    debug_jobs: "任务导出包",
    readiness: "运行就绪",
    artifact_retention: "产物保留干跑",
    artifact_retention_cleanup: "产物清理执行",
    database_backup: "数据库备份包",
    operations_support_bundle: "运维支持包",
    lark_bot_preflight: "机器人上线预检",
    lark_bot_go_live_gate: "机器人真实上线门禁",
    lark_bot_permission_checklist: "机器人权限清单",
    lark_bot_setup_package: "机器人接入交付包"
  };
  return labels[key] ?? key;
}

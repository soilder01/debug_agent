import type { LarkBotGoLiveGate } from "../api/client";
import { MetricStrip, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type LarkBotGoLiveGatePanelProps = {
  gate: LarkBotGoLiveGate;
};

export function LarkBotGoLiveGatePanel({ gate }: LarkBotGoLiveGatePanelProps) {
  return (
    <ProductSurface
      title="机器人真实上线门禁"
      eyebrow="飞书机器人"
      description="汇总运行就绪、机器人预检、管理员确认、权限缺失和命令积压，判断是否允许进入真实飞书 dogfood。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <StatusBadge tone={gateTone(gate.status)}>{gateLabel(gate.status)}</StatusBadge>
      <MetricStrip
        label="机器人上线门禁摘要"
        metrics={[
          { label: "准入结论", value: gate.allowed ? "允许" : "暂不允许", helper: gate.decision },
          { label: "门禁状态", value: gateLabel(gate.status), helper: "综合检查" },
          { label: "事件模式", value: eventModeLabel(gate.preflight.event_mode), helper: "事件接收" },
          { label: "预检状态", value: gateLabel(gate.preflight.status), helper: "机器人上线预检" },
          { label: "待确认命令", value: gate.preflight.pending_command_count, helper: "必须清零" },
          { label: "失败命令", value: gate.preflight.failed_command_count, helper: "需要复盘" }
        ]}
      />
      <section aria-label="机器人真实上线门禁检查项">
        <h3>检查项</h3>
        <ul>
          {gate.checks.map((check) => (
            <li key={check.key}>
              {check.label}：{gateLabel(check.status)} / {check.detail} / {check.action}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="机器人真实上线门禁导出入口">
        <h3>导出入口</h3>
        <ul>
          {Object.entries(gate.export_urls).map(([key, url]) => (
            <li key={key}>
              {gateExportLabel(key)}：{url}
            </li>
          ))}
        </ul>
      </section>
      <div style={{ display: "none" }}>
        <p>机器人真实上线门禁状态：{gateLabel(gate.status)}</p>
        <p>机器人真实上线门禁结论：{gate.allowed ? "允许" : "暂不允许"}</p>
        <p>机器人真实上线门禁说明：{gate.decision}</p>
        <p>机器人真实上线事件模式：{eventModeLabel(gate.preflight.event_mode)}</p>
        {gate.checks.map((check) => (
          <p key={`hidden-${check.key}`}>
            机器人真实上线检查：{check.label}/{gateLabel(check.status)}/{check.action}
          </p>
        ))}
      </div>
    </ProductSurface>
  );
}

function eventModeLabel(eventMode: LarkBotGoLiveGate["preflight"]["event_mode"]): string {
  if (eventMode === "long_connection") {
    return "长连接模式";
  }
  return "webhook 模式";
}

function gateTone(status: LarkBotGoLiveGate["status"] | LarkBotGoLiveGate["checks"][number]["status"]): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "warning") {
    return "warning";
  }
  return "success";
}

function gateLabel(status: LarkBotGoLiveGate["status"] | LarkBotGoLiveGate["checks"][number]["status"]): string {
  if (status === "passed") {
    return "通过";
  }
  if (status === "warning") {
    return "需关注";
  }
  return "阻塞";
}

function gateExportLabel(key: string): string {
  const labels: Record<string, string> = {
    preflight: "机器人上线预检",
    permission_checklist: "机器人权限清单",
    setup_package: "接入交付包",
    setup_acknowledgements: "接入确认记录",
    operation_audits: "Lark 操作审计",
    support_bundle: "运维支持包"
  };
  return labels[key] ?? key;
}

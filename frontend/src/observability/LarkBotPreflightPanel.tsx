import { useState, type FormEvent } from "react";

import type { LarkBotPreflight, LarkBotSetupAcknowledgementRequest } from "../api/client";
import { MetricStrip, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type LarkBotPreflightPanelProps = {
  preflight: LarkBotPreflight;
  onAcknowledgeSetupItem?: (itemKey: string, request: LarkBotSetupAcknowledgementRequest) => Promise<void>;
};

export function LarkBotPreflightPanel({ preflight, onAcknowledgeSetupItem }: LarkBotPreflightPanelProps) {
  const [ackItemKey, setAckItemKey] = useState(preflight.operator_required_items[0]?.key ?? "");
  const [ackActor, setAckActor] = useState("local-dev-operator");
  const [ackEvidence, setAckEvidence] = useState("");
  const [ackNote, setAckNote] = useState("");
  const [ackFeedback, setAckFeedback] = useState("");
  const [isSubmittingAck, setIsSubmittingAck] = useState(false);
  const selectedAckItemKey = ackItemKey || preflight.operator_required_items[0]?.key || "";

  async function handleAcknowledgeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onAcknowledgeSetupItem || !selectedAckItemKey) {
      return;
    }
    setAckFeedback("");
    setIsSubmittingAck(true);
    try {
      await onAcknowledgeSetupItem(selectedAckItemKey, {
        actor: ackActor,
        evidence: ackEvidence,
        note: ackNote
      });
      setAckEvidence("");
      setAckNote("");
      setAckFeedback("接入确认已记录");
    } finally {
      setIsSubmittingAck(false);
    }
  }

  return (
    <ProductSurface
      title="机器人上线预检"
      eyebrow="飞书机器人"
      description={`在接入真实飞书应用前，检查${eventModeLabel(
        preflight.event_mode
      )}、bot 身份、IM 权限清单和待处理命令积压。`}
      className="observability-dashboard observability-dashboard--compact"
    >
      <StatusBadge tone={preflightTone(preflight.status)}>{preflightStatusLabel(preflight.status)}</StatusBadge>
      <MetricStrip
        label="机器人上线预检摘要"
        metrics={[
          {
            label: "事件模式",
            value: eventModeLabel(preflight.event_mode),
            helper: eventModeHelper(preflight.event_mode)
          },
          {
            label: "回调地址",
            value: preflight.event_endpoint_url,
            helper: preflight.event_mode === "long_connection" ? "长连接模式不作为门禁" : "飞书事件订阅 URL"
          },
          {
            label: "连接器",
            value: `${identityLabel(preflight.connector.identity)} / ${preflight.connector.profile || "默认"}`,
            helper: preflight.connector.mode
          },
          { label: "待确认命令", value: preflight.pending_command_count, helper: "上线前建议清零" },
          { label: "失败命令", value: preflight.failed_command_count, helper: "需要复盘" }
        ]}
      />
      <section className="writeback-audit-list" aria-label="真实飞书接入清单">
        <h3>真实接入清单</h3>
        <p>这里列出进入真实飞书应用前，需要用户、管理员或运维明确完成的事项。</p>
        <a className="download-link" href={preflight.setup_package_url} download="debug-agent-lark-bot-setup-package.zip">
          下载接入交付包
        </a>
        <ul aria-label="真实飞书接入事项">
          {preflight.operator_required_items.map((item) => (
            <li className="writeback-audit-list__item" key={item.key}>
              <div>
                <strong>{item.title}</strong>
                <StatusBadge tone={setupStatusTone(item.status)}>{setupStatusLabel(item.status)}</StatusBadge>
              </div>
              <p>
                归属：{setupOwnerLabel(item.owner)} / {item.required ? "必需" : "建议"}
              </p>
              <p>详情：{item.detail}</p>
              <p>下一步：{item.action}</p>
              <p>证据：{item.evidence}</p>
              {item.acknowledgement ? (
                <p>
                  最近确认：{item.acknowledgement.actor} / {item.acknowledgement.created_at} /{" "}
                  {item.acknowledgement.evidence}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
        {onAcknowledgeSetupItem ? (
          <form className="writeback-audit-filters" aria-label="记录飞书接入确认" onSubmit={handleAcknowledgeSubmit}>
            <label>
              确认事项
              <select value={selectedAckItemKey} onChange={(event) => setAckItemKey(event.target.value)}>
                {preflight.operator_required_items.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              确认人
              <input value={ackActor} onChange={(event) => setAckActor(event.target.value)} />
            </label>
            <label>
              证据
              <input
                value={ackEvidence}
                onChange={(event) => setAckEvidence(event.target.value)}
                placeholder="审批单、截图链接、探针报告路径"
                required
              />
            </label>
            <label>
              备注
              <input value={ackNote} onChange={(event) => setAckNote(event.target.value)} />
            </label>
            <button type="submit" disabled={isSubmittingAck || !ackEvidence.trim()}>
              记录确认
            </button>
            {ackFeedback ? <span>{ackFeedback}</span> : null}
          </form>
        ) : null}
      </section>
      <section aria-label="机器人必需权限">
        <h3>必需权限</h3>
        <p>{preflight.required_bot_scopes.join(", ") || "暂无权限清单"}</p>
        {preflight.recent_missing_scopes.length ? (
          <p role="alert">近期缺失权限：{preflight.recent_missing_scopes.join(", ")}</p>
        ) : null}
      </section>
      <section aria-label="机器人上线预检项">
        <h3>检查项</h3>
        <ul>
          {preflight.checks.map((check) => (
            <li key={check.key}>
              {check.label}：{preflightStatusLabel(check.status)} / {check.detail} / {check.action}
            </li>
          ))}
        </ul>
      </section>
      <div style={{ display: "none" }}>
        <p>机器人预检状态：{preflightStatusLabel(preflight.status)}</p>
        <p>机器人事件模式：{eventModeLabel(preflight.event_mode)}</p>
        <p>机器人预检回调地址：{preflight.event_endpoint_url}</p>
        <p>机器人预检身份：{identityLabel(preflight.connector.identity)}</p>
        <p>机器人接入交付包：{preflight.setup_package_url}</p>
        <p>机器人预检待确认：{preflight.pending_command_count}</p>
        <p>机器人预检失败：{preflight.failed_command_count}</p>
        {preflight.operator_required_items.map((item) => (
          <p key={`hidden-setup-${item.key}`}>
            机器人接入事项：{item.title}/{setupStatusLabel(item.status)}/{setupOwnerLabel(item.owner)}
          </p>
        ))}
        {preflight.operator_required_items.map((item) =>
          item.acknowledgement ? (
            <p key={`hidden-ack-${item.key}`}>
              机器人接入确认：{item.title}/{item.acknowledgement.actor}/{item.acknowledgement.evidence}
            </p>
          ) : null
        )}
        {preflight.checks.map((check) => (
          <p key={`hidden-${check.key}`}>
            机器人预检项：{check.label}/{preflightStatusLabel(check.status)}/{check.action}
          </p>
        ))}
      </div>
    </ProductSurface>
  );
}

function eventModeLabel(eventMode: LarkBotPreflight["event_mode"]): string {
  if (eventMode === "long_connection") {
    return "长连接模式";
  }
  return "webhook 模式";
}

function eventModeHelper(eventMode: LarkBotPreflight["event_mode"]): string {
  if (eventMode === "long_connection") {
    return "小D bot 长连接";
  }
  return "HTTP webhook";
}

function preflightTone(status: "passed" | "warning" | "failed"): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "warning") {
    return "warning";
  }
  return "success";
}

function preflightStatusLabel(status: "passed" | "warning" | "failed"): string {
  if (status === "passed") {
    return "通过";
  }
  if (status === "warning") {
    return "需关注";
  }
  return "阻塞";
}

function identityLabel(identity: string): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}

function setupStatusTone(status: "done" | "needs_action" | "manual_check"): "critical" | "warning" | "success" | "neutral" {
  if (status === "done") {
    return "success";
  }
  if (status === "needs_action") {
    return "critical";
  }
  return "warning";
}

function setupStatusLabel(status: "done" | "needs_action" | "manual_check"): string {
  if (status === "done") {
    return "已完成";
  }
  if (status === "needs_action") {
    return "需要处理";
  }
  return "需人工确认";
}

function setupOwnerLabel(owner: string): string {
  if (owner === "debug_agent_operator") {
    return "Debug Agent 运维";
  }
  if (owner === "lark_app_admin") {
    return "飞书应用管理员";
  }
  if (owner === "workspace_admin") {
    return "飞书空间管理员";
  }
  if (owner === "security_admin") {
    return "安全管理员";
  }
  return "未知";
}

import type { LarkSpreadsheetStatus } from "../api/client";
import { StatusBadge } from "../ui/ProductPrimitives";
import { displayStatus } from "../ui/statusLabels";

type LarkSpreadsheetStatusPanelProps = {
  status: LarkSpreadsheetStatus;
};

export function LarkSpreadsheetStatusPanel({ status }: LarkSpreadsheetStatusPanelProps) {
  const connectivityLabel = displayStatus(status.connectivity_status);
  return (
    <>
      <StatusBadge tone={status.connectivity_status === "ok" ? "success" : "critical"}>{connectivityLabel}</StatusBadge>
      <p>Lark 配置状态：{status.configured ? "已配置" : "未配置"}</p>
      <p>Lark 连接状态：{connectivityLabel}</p>
      <p>
        Lark 表格：{status.spreadsheet_id || "无"} / {status.sheet_id || "无"}
      </p>
      <p>Lark CLI 超时：{status.lark_cli_timeout_seconds}s</p>
      <p>
        Lark Connector：{status.connector_mode ?? "cli"} / 身份 {connectorIdentityLabel(status.connector_identity)} / Profile{" "}
        {status.connector_profile || "默认"}
      </p>
      <p>
        Lark 授权状态：{status.connector_auth_status ?? "unknown"} / Token {status.connector_token_status ?? "unknown"}
      </p>
      {status.error_type ? <p>Lark 错误类型：{connectorErrorTypeLabel(status.error_type)}</p> : null}
      {status.permission_scopes?.length ? <p>Lark 缺少权限：{status.permission_scopes.join(", ")}</p> : null}
      {status.console_url ? <p>Lark 权限配置入口：{status.console_url}</p> : null}
      {status.risk_action ? <p>Lark 高风险操作：{status.risk_action}</p> : null}
      {status.error_message ? <p>Lark 错误：{status.error_message}</p> : null}
    </>
  );
}

function connectorIdentityLabel(identity: string | undefined): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}

function connectorErrorTypeLabel(errorType: string): string {
  const labels: Record<string, string> = {
    permission_denied: "权限不足",
    auth_required: "需要授权",
    auth_expired: "授权过期",
    confirmation_required: "需要确认高风险操作",
    timeout: "执行超时",
    missing_executable: "CLI 未安装",
    client_not_configured: "客户端未配置",
    command_not_allowed: "命令未被允许"
  };
  return labels[errorType] ?? errorType;
}

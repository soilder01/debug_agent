import type { LarkSpreadsheetStatus } from "../api/client";
import { StatusBadge } from "../ui/ProductPrimitives";

type LarkSpreadsheetStatusPanelProps = {
  status: LarkSpreadsheetStatus;
};

export function LarkSpreadsheetStatusPanel({ status }: LarkSpreadsheetStatusPanelProps) {
  return (
    <>
      <StatusBadge tone={status.connectivity_status === "ok" ? "success" : "critical"}>{status.connectivity_status}</StatusBadge>
      <p>Lark 配置状态：{status.configured ? "已配置" : "未配置"}</p>
      <p>Lark 连接状态：{status.connectivity_status}</p>
      <p>
        Lark 表格：{status.spreadsheet_id || "无"} / {status.sheet_id || "无"}
      </p>
      <p>Lark CLI 超时：{status.lark_cli_timeout_seconds}s</p>
      {status.error_message ? <p>Lark 错误：{status.error_message}</p> : null}
    </>
  );
}

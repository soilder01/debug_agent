import type { LarkOperationAudit } from "../api/client";
import { displayStatus } from "../ui/statusLabels";

type LarkOperationAuditListProps = {
  audits: LarkOperationAudit[];
  totalCount: number;
  activeFilter: string | null;
  onLoadStatus: (status: string | null) => void;
  onLoadMore: () => void;
};

export function LarkOperationAuditList({
  audits,
  totalCount,
  activeFilter,
  onLoadStatus,
  onLoadMore
}: LarkOperationAuditListProps) {
  return (
    <section className="writeback-audit-list" aria-label="Lark 操作审计列表">
      <p>Lark 操作审计总数：{totalCount}</p>
      <p>当前筛选：{operationFilterLabel(activeFilter)}</p>
      <div className="writeback-audit-filters">
        <button type="button" onClick={() => onLoadStatus(null)}>
          查看全部操作
        </button>
        <button type="button" onClick={() => onLoadStatus("succeeded")}>
          查看成功操作
        </button>
        <button type="button" onClick={() => onLoadStatus("failed")}>
          查看失败操作
        </button>
      </div>
      {audits.length === 0 ? (
        <p>暂无 Lark 操作审计。</p>
      ) : (
        <ul aria-label="Lark 操作审计记录">
          {audits.map((audit) => (
            <li className="writeback-audit-list__item" key={audit.audit_id}>
              <p>
                {audit.service} {audit.operation}：{displayStatus(audit.status)}
              </p>
              <p>
                身份：{connectorIdentityLabel(audit.identity)} / Profile {audit.profile || "默认"} / 耗时 {audit.duration_ms}ms
              </p>
              <p>上下文：{audit.context || "无"}</p>
              {audit.error_type ? <p>错误类型：{operationErrorTypeLabel(audit.error_type)}</p> : null}
              {audit.permission_scopes.length ? <p>缺少权限：{audit.permission_scopes.join(", ")}</p> : null}
              {audit.hint ? <p>修复提示：{audit.hint}</p> : null}
              {audit.console_url ? <p>权限配置入口：{audit.console_url}</p> : null}
              {audit.risk_action ? <p>高风险操作：{audit.risk_action}</p> : null}
            </li>
          ))}
        </ul>
      )}
      {audits.length < totalCount ? (
        <button type="button" onClick={onLoadMore}>
          加载更多 Lark 操作
        </button>
      ) : null}
    </section>
  );
}

export function operationFilterLabel(status: string | null): string {
  if (status === "succeeded") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  return "全部";
}

function connectorIdentityLabel(identity: string): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}

function operationErrorTypeLabel(errorType: string): string {
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

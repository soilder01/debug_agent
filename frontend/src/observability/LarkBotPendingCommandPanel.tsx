import type { LarkBotPendingCommand, LarkBotReplyPayload } from "../api/client";
import { ActionRow, EmptyState, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type LarkBotPendingCommandPanelProps = {
  commands: LarkBotPendingCommand[];
  totalCount: number;
  activeStatus: string | null;
  replyPreview: LarkBotReplyPayload | null;
  onLoadStatus: (status: string | null) => void;
  onLoadMore: () => void;
  onConfirm: (commandId: string) => void;
  onPreviewReply: (commandId: string) => void;
};

export function LarkBotPendingCommandPanel({
  commands,
  totalCount,
  activeStatus,
  replyPreview,
  onLoadStatus,
  onLoadMore,
  onConfirm,
  onPreviewReply
}: LarkBotPendingCommandPanelProps) {
  return (
    <ProductSurface
      title="飞书机器人命令"
      eyebrow="机器人入口"
      description="查看飞书机器人产生的写风险命令，确认后才会提交 Debug 任务。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <p>机器人命令总数：{totalCount}</p>
      <p>当前筛选：{botCommandFilterLabel(activeStatus)}</p>
      <ActionRow label="机器人命令筛选">
        <button type="button" onClick={() => onLoadStatus(null)}>
          查看全部机器人命令
        </button>
        <button type="button" onClick={() => onLoadStatus("pending")}>
          查看待确认命令
        </button>
        <button type="button" onClick={() => onLoadStatus("executed")}>
          查看已执行命令
        </button>
        <button type="button" onClick={() => onLoadStatus("failed")}>
          查看失败命令
        </button>
      </ActionRow>
      {commands.length === 0 ? (
        <EmptyState title="暂无机器人命令" description="飞书机器人写风险命令会在这里等待确认和审计。" />
      ) : (
        <ul aria-label="飞书机器人命令列表" className="writeback-audit-list">
          {commands.map((command) => (
            <li className="writeback-audit-list__item" key={command.command_id}>
              <p>
                <strong>{command.command_text || command.command_id}</strong>
              </p>
              <p>
                <StatusBadge tone={botCommandStatusTone(command.status)}>{botCommandStatusLabel(command.status)}</StatusBadge>
              </p>
              <p>
                操作者：{command.actor || command.open_id || "未知"} / 操作：{botActionLabel(command.action_kind)} / 身份：
                {botIdentityLabel(command.identity)}
              </p>
              <p>
                群聊：{command.chat_id || "无"} / 原消息：{command.message_id || "无"} / 过期：{command.expires_at || "无"}
              </p>
              {command.confirmed_by ? <p>确认人：{command.confirmed_by}</p> : null}
              {command.error_message ? <p role="alert">执行错误：{command.error_message}</p> : null}
              <ActionRow label={`机器人命令 ${command.command_id} 操作`}>
                {command.status === "pending" ? (
                  <button type="button" onClick={() => onConfirm(command.command_id)}>
                    确认并执行机器人命令
                  </button>
                ) : null}
                <button type="button" onClick={() => onPreviewReply(command.command_id)}>
                  预览机器人回复
                </button>
              </ActionRow>
            </li>
          ))}
        </ul>
      )}
      {commands.length < totalCount ? (
        <button type="button" onClick={onLoadMore}>
          加载更多机器人命令
        </button>
      ) : null}
      {replyPreview ? (
        <section aria-label="机器人回复预览" className="writeback-audit-list__item">
          <h3>机器人回复预览</h3>
          <p>
            目标：{replyTargetLabel(replyPreview)} / 幂等键：{replyPreview.idempotency_key}
          </p>
          <pre>{replyPreview.markdown}</pre>
          <p>投递参数：{replyPreview.delivery_args.join(" ") || "无"}</p>
        </section>
      ) : null}
    </ProductSurface>
  );
}

export function botCommandFilterLabel(status: string | null): string {
  if (status === "pending") {
    return "待确认";
  }
  if (status === "executed") {
    return "已执行";
  }
  if (status === "failed") {
    return "失败";
  }
  return "全部";
}

function botCommandStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "待确认",
    confirmed: "已确认",
    executed: "已执行",
    failed: "失败",
    expired: "已过期"
  };
  return labels[status] ?? status;
}

function botCommandStatusTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed" || status === "expired") {
    return "critical";
  }
  if (status === "pending" || status === "confirmed") {
    return "warning";
  }
  if (status === "executed") {
    return "success";
  }
  return "neutral";
}

function botActionLabel(actionKind: string): string {
  if (actionKind === "submit_case") {
    return "提交单样本调试";
  }
  if (actionKind === "submit_batch") {
    return "提交批量调试";
  }
  return actionKind || "未知";
}

function botIdentityLabel(identity: string): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}

function replyTargetLabel(replyPreview: LarkBotReplyPayload): string {
  if (replyPreview.target_type === "message") {
    return `原消息 ${replyPreview.message_id}`;
  }
  if (replyPreview.target_type === "chat") {
    return `群聊 ${replyPreview.chat_id}`;
  }
  if (replyPreview.target_type === "user") {
    return `用户 ${replyPreview.user_id}`;
  }
  return "无可投递目标";
}

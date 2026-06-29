import type { LarkNotificationOutbox } from "../api/client";
import { ActionRow, EmptyState, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type LarkNotificationOutboxPanelProps = {
  notifications: LarkNotificationOutbox[];
  totalCount: number;
  activeStatus: string | null;
  onLoadStatus: (status: string | null) => void;
  onLoadMore: () => void;
};

export function LarkNotificationOutboxPanel({
  notifications,
  totalCount,
  activeStatus,
  onLoadStatus,
  onLoadMore
}: LarkNotificationOutboxPanelProps) {
  return (
    <ProductSurface
      title="飞书通知 Outbox"
      eyebrow="小D投递"
      description="查看小D消息投递状态、重试次数和最近失败原因。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <p>通知总数：{totalCount}</p>
      <p>当前筛选：{notificationStatusLabel(activeStatus)}</p>
      <ActionRow label="飞书通知筛选">
        <button type="button" onClick={() => onLoadStatus(null)}>
          查看全部通知
        </button>
        <button type="button" onClick={() => onLoadStatus("pending")}>
          查看待投递通知
        </button>
        <button type="button" onClick={() => onLoadStatus("sent")}>
          查看已投递通知
        </button>
        <button type="button" onClick={() => onLoadStatus("failed")}>
          查看失败通知
        </button>
      </ActionRow>
      {notifications.length === 0 ? (
        <EmptyState title="暂无飞书通知" description="小D待投递和失败通知会在这里展示。" />
      ) : (
        <ul aria-label="飞书通知 Outbox 列表" className="writeback-audit-list">
          {notifications.map((notification) => (
            <li className="writeback-audit-list__item" key={notification.notification_id}>
              <p>
                <strong>{notification.notification_id}</strong>
              </p>
              <p>
                状态：
                <StatusBadge tone={notificationStatusTone(notification.status)}>
                  {notificationStatusLabel(notification.status)}
                </StatusBadge>
              </p>
              <p>
                类型：{notificationKindLabel(notification.kind)} / 任务：{notification.job_id || "无"} /
                样本：{notification.case_id || "无"}
              </p>
              <p>
                草稿：{notification.draft_id || "无"} / 去重键：{notification.dedupe_key || "无"}
              </p>
              <p>
                重试次数：{notification.attempts} / 更新时间：{notification.updated_at || "无"} / 已投递：
                {notification.sent_at || "否"}
              </p>
              {notification.last_error ? <p role="alert">最近错误：{notification.last_error}</p> : null}
            </li>
          ))}
        </ul>
      )}
      {notifications.length < totalCount ? (
        <button type="button" onClick={onLoadMore}>
          加载更多通知
        </button>
      ) : null}
    </ProductSurface>
  );
}

export function notificationStatusLabel(status: string | null): string {
  if (status === "pending") {
    return "待投递";
  }
  if (status === "sent") {
    return "已投递";
  }
  if (status === "failed") {
    return "失败";
  }
  return "全部";
}

function notificationStatusTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "pending") {
    return "warning";
  }
  if (status === "sent") {
    return "success";
  }
  return "neutral";
}

function notificationKindLabel(kind: string): string {
  if (kind === "badcase_completion") {
    return "完成通知";
  }
  if (kind === "badcase_progress") {
    return "进度通知";
  }
  return kind || "未知";
}

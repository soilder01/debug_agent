import type { LarkBotBadcaseDraft, LarkBotBadcaseDraftConfirmResponse } from "../api/client";
import { ActionRow, EmptyState, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";

type LarkBotBadcaseDraftPanelProps = {
  drafts: LarkBotBadcaseDraft[];
  totalCount: number;
  activeStatus: string | null;
  lastConfirmation: LarkBotBadcaseDraftConfirmResponse | null;
  onLoadStatus: (status: string | null) => void;
  onLoadMore: () => void;
  onConfirm: (draftId: string) => void;
};

export function LarkBotBadcaseDraftPanel({
  drafts,
  totalCount,
  activeStatus,
  lastConfirmation,
  onLoadStatus,
  onLoadMore,
  onConfirm
}: LarkBotBadcaseDraftPanelProps) {
  return (
    <ProductSurface
      title="飞书 badcase 草稿"
      eyebrow="Bot Intake"
      description="查看小D从飞书对话收集到的 badcase 信息，信息齐全后再确认创建 Debug 任务。"
      className="observability-dashboard observability-dashboard--compact"
    >
      <p>badcase 草稿总数：{totalCount}</p>
      <p>当前筛选：{badcaseDraftFilterLabel(activeStatus)}</p>
      <ActionRow label="badcase 草稿筛选">
        <button type="button" onClick={() => onLoadStatus(null)}>
          查看全部草稿
        </button>
        <button type="button" onClick={() => onLoadStatus("needs_more_info")}>
          查看待补充草稿
        </button>
        <button type="button" onClick={() => onLoadStatus("ready_for_confirmation")}>
          查看待确认草稿
        </button>
        <button type="button" onClick={() => onLoadStatus("submitted")}>
          查看已提交草稿
        </button>
        <button type="button" onClick={() => onLoadStatus("completed")}>
          查看已通知草稿
        </button>
        <button type="button" onClick={() => onLoadStatus("cancelled")}>
          查看已取消草稿
        </button>
      </ActionRow>
      {drafts.length === 0 ? (
        <EmptyState title="暂无 badcase 草稿" description="小D从飞书对话收集的 badcase 会在这里展示。" />
      ) : (
        <ul aria-label="飞书 badcase 草稿列表" className="writeback-audit-list">
          {drafts.map((draft) => (
            <li className="writeback-audit-list__item" key={draft.draft_id}>
              <p>
                <strong>{draft.issue_summary || draft.input_source || draft.draft_id}</strong>
              </p>
              <p>
                <StatusBadge tone={badcaseDraftStatusTone(draft.status)}>
                  {badcaseDraftStatusLabel(draft.status)}
                </StatusBadge>
              </p>
              <p>
                提交人：{draft.actor || draft.open_id || "未知"} / 会话：{draft.chat_id || "无"} / 消息：
                {draft.message_id || "无"}
              </p>
              <p>原始输入：{draft.input_source || "待补充"}</p>
              <p>模型输出：{draft.model_output || "待补充"}</p>
              <p>期望结果：{draft.expected_output || "待补充"}</p>
              <p>错误现象：{draft.issue_summary || "待补充"}</p>
              {draft.links.length > 0 ? (
                <p>
                  链接：
                  {draft.links.map((link) => (
                    <a href={link} key={link} rel="noreferrer" target="_blank">
                      {link}
                    </a>
                  ))}
                </p>
              ) : null}
              {linkContextItems(draft).length > 0 ? (
                <ul aria-label={`badcase 草稿 ${draft.draft_id} 链接上下文`}>
                  {linkContextItems(draft).map((context) => (
                    <li key={stringValue(context.url)}>
                      {stringValue(context.resource) || "链接"}：{stringValue(context.link_type)}
                      {stringValue(context.status) ? ` / ${linkContextStatusLabel(stringValue(context.status))}` : ""}
                      {stringValue(context.token) ? ` / token=${stringValue(context.token)}` : ""}
                      {stringValue(context.sheet_id) ? ` / sheet=${stringValue(context.sheet_id)}` : ""}
                      {stringValue(context.selected_row) ? ` / row=${stringValue(context.selected_row)}` : ""}
                      {stringValue(context.table_id) ? ` / table=${stringValue(context.table_id)}` : ""}
                      {stringValue(context.selected_record) ? ` / record=${stringValue(context.selected_record)}` : ""}
                      {stringValue(context.error_type) ? ` / error=${stringValue(context.error_type)}` : ""}
                      {stringValue(mediaInput(context).status)
                        ? ` / media=${linkContextStatusLabel(stringValue(mediaInput(context).status))}`
                        : ""}
                      {stringValue(mediaInput(context).attachment_token)
                        ? ` / attachment=${stringValue(mediaInput(context).attachment_token)}`
                        : ""}
                      {linkContextPermissionScopes(context).length > 0
                        ? ` / missing_scope=${linkContextPermissionScopes(context).join(",")}`
                        : ""}
                      {stringValue(context.next_action) ? ` / ${stringValue(context.next_action)}` : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
              {draft.attachments.length > 0 ? <p>附件数量：{draft.attachments.length}</p> : null}
              {draft.missing_fields.length > 0 ? (
                <p>待补充：{draft.missing_fields.map(badcaseFieldLabel).join("、")}</p>
              ) : null}
              {draft.submitted_job_id ? <p>已创建任务：{draft.submitted_job_id}</p> : null}
              {draft.error_message ? <p role="alert">提交错误：{draft.error_message}</p> : null}
              <ActionRow label={`badcase 草稿 ${draft.draft_id} 操作`}>
                {draft.status === "ready_for_confirmation" ? (
                  <button type="button" onClick={() => onConfirm(draft.draft_id)}>
                    确认并创建 Debug 任务
                  </button>
                ) : null}
              </ActionRow>
            </li>
          ))}
        </ul>
      )}
      {drafts.length < totalCount ? (
        <button type="button" onClick={onLoadMore}>
          加载更多 badcase 草稿
        </button>
      ) : null}
      {lastConfirmation ? (
        <section aria-label="badcase 草稿确认结果" className="writeback-audit-list__item">
          <h3>badcase 草稿确认结果</h3>
          <p>草稿状态：{badcaseDraftStatusLabel(lastConfirmation.draft.status)}</p>
          <p>样本追踪号：{lastConfirmation.draft.submitted_case_id || "无"}</p>
          <p>任务编号：{lastConfirmation.submitted_job?.job_id || lastConfirmation.draft.submitted_job_id || "无"}</p>
        </section>
      ) : null}
    </ProductSurface>
  );
}

export function badcaseDraftFilterLabel(status: string | null): string {
  if (status === "needs_more_info") {
    return "待补充";
  }
  if (status === "ready_for_confirmation") {
    return "待确认";
  }
  if (status === "submitted") {
    return "已提交";
  }
  if (status === "completed") {
    return "已通知";
  }
  if (status === "cancelled") {
    return "已取消";
  }
  if (status === "failed") {
    return "失败";
  }
  return "全部";
}

function badcaseDraftStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    needs_more_info: "待补充",
    ready_for_confirmation: "待确认",
    submitted: "已提交",
    completed: "已通知",
    cancelled: "已取消",
    failed: "失败"
  };
  return labels[status] ?? status;
}

function badcaseDraftStatusTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed" || status === "cancelled") {
    return "critical";
  }
  if (status === "needs_more_info" || status === "ready_for_confirmation") {
    return "warning";
  }
  if (status === "submitted" || status === "completed") {
    return "success";
  }
  return "neutral";
}

function badcaseFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    input_source: "原始输入",
    model_output: "模型输出",
    expected_output: "期望结果",
    issue_summary: "错误现象"
  };
  return labels[field] ?? field;
}

function linkContextItems(draft: LarkBotBadcaseDraft): Record<string, unknown>[] {
  return draft.attachments.filter(
    (item): item is Record<string, unknown> => item.type === "link_context"
  );
}

function linkContextStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    metadata_only: "已识别链接",
    recognized: "已识别",
    content_resolved: "已读取并提取字段",
    content_read: "已读取内容",
    needs_locator: "需要补充定位",
    read_failed: "读取失败",
    reader_not_supported: "暂不支持读取",
    downloaded: "已下载附件",
    download_failed: "附件下载失败",
    missing_attachment: "缺少附件下载信息"
  };
  return labels[status] ?? status;
}

function mediaInput(context: Record<string, unknown>): Record<string, unknown> {
  return isRecord(context.media_input) ? context.media_input : {};
}

function linkContextPermissionScopes(context: Record<string, unknown>): string[] {
  const ownScopes = stringArrayValue(context.permission_scopes);
  if (ownScopes.length > 0) {
    return ownScopes;
  }
  return stringArrayValue(mediaInput(context).permission_scopes);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import type { LarkWriteConfirmation, SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { ActionRow, ProductSurface, StatusBadge } from "../ui/ProductPrimitives";
import { NativeWritebackFields } from "./NativeWritebackFields";

type SpreadsheetWritebackPanelProps = {
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  writeConfirmation?: LarkWriteConfirmation | null;
  onWriteReport: () => void;
  onPrepareWriteConfirmation?: () => void;
  onConfirmWriteReport?: () => void;
  onLoadAudit: () => void;
};

export function SpreadsheetWritebackPanel({
  writebackResult,
  writebackAudit,
  writeConfirmation = null,
  onWriteReport,
  onPrepareWriteConfirmation,
  onConfirmWriteReport,
  onLoadAudit
}: SpreadsheetWritebackPanelProps) {
  const hasAuditPreview = Boolean(writebackAudit);
  const [isAuditPreviewOpen, setIsAuditPreviewOpen] = useState(hasAuditPreview);
  const auditPreviewSignature = useMemo(
    () =>
      writebackAudit
        ? `${writebackAudit.job_id}:${writebackAudit.status}:${writebackAudit.row_id}:${writebackAudit.updated_at}:${writebackAudit.error_message}`
        : "none",
    [writebackAudit]
  );
  const auditStatusText = writebackAudit ? writebackStatusLabel(writebackAudit.status) : "";

  useEffect(() => {
    setIsAuditPreviewOpen(hasAuditPreview);
  }, [auditPreviewSignature, hasAuditPreview]);

  const auditPreviewDrawer =
    writebackAudit && isAuditPreviewOpen ? (
      <aside className="writeback-audit-drawer writeback-audit-drawer--report" aria-label="写回审计预览">
        <div className="writeback-audit-drawer__header">
          <div>
            <p className="writeback-panel-heading__eyebrow">审计预览</p>
            <h3>最近一次写回审计</h3>
            <p>任务：{writebackAudit.job_id}</p>
          </div>
          <button type="button" aria-label="关闭写回审计预览" onClick={() => setIsAuditPreviewOpen(false)}>
            关闭
          </button>
        </div>
        <StatusBadge tone={writebackTone(writebackAudit.status)}>{auditStatusText}</StatusBadge>
        <p>写回审计状态：{auditStatusText}</p>
        <p>写回行：{writebackAudit.row_id || "无"}</p>
        <p>报告链接：{writebackAudit.report_url || "无"}</p>
        <p>更新时间：{writebackAudit.updated_at}</p>
        {writebackAudit.error_message ? <p role="alert">写回审计错误：{writebackAudit.error_message}</p> : null}
        <NativeWritebackFields fields={writebackAudit.fields} />
        {Object.keys(writebackAudit.fields).length > 0 ? (
          <ul aria-label="写回审计字段">
            {Object.entries(writebackAudit.fields).map(([key, value]) => (
              <li key={key}>
                {key}：{value}
              </li>
            ))}
          </ul>
        ) : null}
      </aside>
    ) : null;

  return (
    <ProductSurface
      title="飞书写回"
      eyebrow="写回"
      description="把最终 debug 结论写回表格，并在右侧预览最近一次写回审计。"
      className="writeback-panel"
    >
      <ActionRow label="飞书写回操作">
        <button type="button" onClick={onWriteReport}>
          写回报告到表格
        </button>
        {onPrepareWriteConfirmation ? (
          <button type="button" onClick={onPrepareWriteConfirmation}>
            生成高风险写回确认
          </button>
        ) : null}
        {onConfirmWriteReport ? (
          <button type="button" onClick={onConfirmWriteReport} disabled={!writeConfirmation}>
            确认并写回报告
          </button>
        ) : null}
        <button type="button" onClick={onLoadAudit}>
          加载审计预览
        </button>
      </ActionRow>
      {writeConfirmation ? (
        <section aria-label="Lark 写回确认单" className="writeback-audit-list">
          <p>Lark 写回确认状态：{writeConfirmationStatusLabel(writeConfirmation.status)}</p>
          <p>风险操作：{writeConfirmation.risk_action}</p>
          <p>目标资源：{writeConfirmation.resource_summary}</p>
          <p>需要 scope：{writeConfirmation.required_scopes.join(", ") || "未声明"}</p>
          <p>确认过期时间：{writeConfirmation.expires_at}</p>
          {writeConfirmation.confirmed_at ? <p>确认时间：{writeConfirmation.confirmed_at}</p> : null}
        </section>
      ) : null}
      {writebackResult ? (
        <>
          <p>表格写回行：{writebackResult.row_id}</p>
          <NativeWritebackFields fields={writebackResult.fields} />
          <ul aria-label="表格写回字段">
            {Object.entries(writebackResult.fields).map(([key, value]) => (
              <li key={key}>
                {key}：{value}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {auditPreviewDrawer ? createPortal(auditPreviewDrawer, document.body) : null}
    </ProductSurface>
  );
}

function writebackStatusLabel(status: string): string {
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  if (status === "succeeded") {
    return "成功";
  }
  return status || "未知";
}

function writeConfirmationStatusLabel(status: string): string {
  if (status === "confirmed") {
    return "已确认";
  }
  if (status === "pending") {
    return "待确认";
  }
  if (status === "expired") {
    return "已过期";
  }
  return status || "未知";
}

function writebackTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "skipped") {
    return "warning";
  }
  if (status === "succeeded") {
    return "success";
  }
  return "neutral";
}

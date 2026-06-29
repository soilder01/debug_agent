import { useEffect, useMemo, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { createPortal } from "react-dom";

import type {
  LarkAuthSession,
  LarkOperationAuditListResponse,
  LarkScopeCheckResponse,
  LarkSpreadsheetStatus,
  SpreadsheetSyncResponse,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackAuditCounts,
  SpreadsheetWritebackAuditListResponse,
  SpreadsheetWritebackResult
} from "../api/client";
import { ProductSurface } from "../ui/ProductPrimitives";
import { LarkOperationAuditList } from "./LarkOperationAuditList";
import { LarkAuthSessionPanel } from "./LarkAuthSessionPanel";
import { LarkScopeRepairPanel } from "./LarkScopeRepairPanel";
import { LarkSpreadsheetStatusPanel } from "./LarkSpreadsheetStatusPanel";
import { SpreadsheetControlsPanel } from "./SpreadsheetControlsPanel";
import { SpreadsheetSyncResultPanel } from "./SpreadsheetSyncResultPanel";
import { WritebackAuditList } from "./WritebackAuditList";
import { WritebackAuditSummary } from "./WritebackAuditSummary";

gsap.registerPlugin(useGSAP);

type SpreadsheetSyncPanelProps = {
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  rerunRowIds: string;
  rerunAutoClosure: boolean;
  rerunWriteback: boolean;
  larkSpreadsheetStatus: LarkSpreadsheetStatus | null;
  syncResult: SpreadsheetSyncResponse | null;
  writebackAuditSummary: SpreadsheetWritebackAuditCounts | null;
  writebackAuditList: SpreadsheetWritebackAuditListResponse | null;
  activeWritebackAuditStatus: string | null;
  larkOperationAuditList: LarkOperationAuditListResponse | null;
  activeLarkOperationAuditStatus: string | null;
  larkScopeCheck: LarkScopeCheckResponse | null;
  larkAuthSession: LarkAuthSession | null;
  writebackResult: SpreadsheetWritebackResult | null;
  batchExportHref?: string;
  onSpreadsheetUrlChange: (value: string) => void;
  onSpreadsheetIdChange: (value: string) => void;
  onSheetIdChange: (value: string) => void;
  onRerunRowIdsChange: (value: string) => void;
  onRerunAutoClosureChange: (value: boolean) => void;
  onRerunWritebackChange: (value: boolean) => void;
  onUseSpreadsheetUrl: () => void;
  onCheckLarkStatus: () => void;
  onSyncSpreadsheet: () => void;
  onRerunSpreadsheetRows: () => void;
  onLoadWritebackAuditSummary: () => void;
  onLoadWritebackAudits: (status: string | null) => void;
  onLoadLarkOperationAudits: (status: string | null) => void;
  onCheckLarkScopes: () => void;
  onCreateLarkAuthSession: () => void;
  onCompleteLarkAuthSession: () => void;
  onOpenAuditJob: (jobId: string) => void;
  onRetryAudit: (audit: SpreadsheetWritebackAudit) => void;
  onLoadMoreWritebackAudits: () => void;
  onLoadMoreLarkOperationAudits: () => void;
};

type WritebackMood = "idle" | "active" | "success" | "alert";
type WorkerExpression = "neutral" | "smile" | "concern";

function writebackMood(
  larkSpreadsheetStatus: LarkSpreadsheetStatus | null,
  syncResult: SpreadsheetSyncResponse | null,
  writebackAuditList: SpreadsheetWritebackAuditListResponse | null,
): WritebackMood {
  if (writebackAuditList?.audits.some((audit) => audit.status === "failed")) {
    return "alert";
  }
  if (syncResult && syncResult.rejected_rows.length === 0 && syncResult.imported_case_ids.length > 0) {
    return "success";
  }
  if (larkSpreadsheetStatus?.connectivity_status === "ok") {
    return "active";
  }
  return "idle";
}

function workerExpression(role: "connector" | "carrier" | "auditor", mood: WritebackMood): WorkerExpression {
  if (mood === "idle") {
    return "neutral";
  }
  if (mood === "alert" && role === "auditor") {
    return "concern";
  }
  return "smile";
}

function WritebackCrewStage({
  mood,
  importedCount,
  failedAuditCount,
}: {
  mood: WritebackMood;
  importedCount: number;
  failedAuditCount: number;
}) {
  const caption = {
    idle: "巡逻待命",
    active: "连接巡检",
    success: "任务搬运",
    alert: "审计警戒",
  }[mood];
  const crew = [
    { role: "connector" as const, name: "连接员", color: "blue", prop: "链" },
    { role: "carrier" as const, name: "搬运员", color: "green", prop: "箱" },
    { role: "auditor" as const, name: "审计员", color: "orange", prop: "镜" },
  ];

  return (
    <section className="writeback-crew-stage" aria-label="回写调度小队" data-writeback-mood={mood}>
      <div className="writeback-crew-stage__copy">
        <p className="writeback-crew-stage__eyebrow">回写调度小队</p>
        <h3>{caption}</h3>
        <p>
          {importedCount > 0 ? `已搬运 ${importedCount} 个样本` : "未启动时保持巡逻、热身和工具校准。"}
          {failedAuditCount > 0 ? ` 发现 ${failedAuditCount} 条失败审计。` : ""}
        </p>
      </div>
      <div className="writeback-crew-stage__track" aria-hidden="true">
        <span className="writeback-crew-stage__rail" />
        <span className="writeback-crew-stage__package" />
      </div>
      <div className="writeback-crew">
        {crew.map((worker) => {
          const expression = workerExpression(worker.role, mood);
          return (
            <div
              key={worker.role}
              className="writeback-worker"
              aria-label={`调度小人-${worker.name}`}
              data-worker-color={worker.color}
              data-worker-expression={expression}
            >
              <span className="writeback-worker__head">
                <span className="writeback-worker__eye" />
                <span className="writeback-worker__eye" />
                <span className="writeback-worker__mouth" />
              </span>
              <span className="writeback-worker__body">
                <span className="writeback-worker__prop">{worker.prop}</span>
              </span>
              <span className="writeback-worker__label">{worker.name}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function filterLabel(status: string | null): string {
  if (status === "succeeded") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  return "全部";
}

export function SpreadsheetSyncPanel({
  spreadsheetUrl,
  spreadsheetId,
  sheetId,
  rerunRowIds,
  rerunAutoClosure,
  rerunWriteback,
  larkSpreadsheetStatus,
  syncResult,
  writebackAuditSummary,
  writebackAuditList,
  activeWritebackAuditStatus,
  larkOperationAuditList,
  activeLarkOperationAuditStatus,
  larkScopeCheck,
  larkAuthSession,
  writebackResult,
  batchExportHref,
  onSpreadsheetUrlChange,
  onSpreadsheetIdChange,
  onSheetIdChange,
  onRerunRowIdsChange,
  onRerunAutoClosureChange,
  onRerunWritebackChange,
  onUseSpreadsheetUrl,
  onCheckLarkStatus,
  onSyncSpreadsheet,
  onRerunSpreadsheetRows,
  onLoadWritebackAuditSummary,
  onLoadWritebackAudits,
  onLoadLarkOperationAudits,
  onCheckLarkScopes,
  onCreateLarkAuthSession,
  onCompleteLarkAuthSession,
  onOpenAuditJob,
  onRetryAudit,
  onLoadMoreWritebackAudits,
  onLoadMoreLarkOperationAudits
}: SpreadsheetSyncPanelProps) {
  const panelRef = useRef<HTMLElement | null>(null);
  const mood = writebackMood(larkSpreadsheetStatus, syncResult, writebackAuditList);
  const failedAuditCount = writebackAuditList?.audits.filter((audit) => audit.status === "failed").length ?? 0;
  const hasWritebackAuditPreview = Boolean(writebackAuditSummary || writebackAuditList);
  const hasLarkOperationAuditPreview = Boolean(larkOperationAuditList);
  const [isAuditPreviewOpen, setIsAuditPreviewOpen] = useState(hasWritebackAuditPreview);
  const [isLarkOperationAuditOpen, setIsLarkOperationAuditOpen] = useState(hasLarkOperationAuditPreview);
  const resultSignature = useMemo(
    () => `${larkSpreadsheetStatus?.connectivity_status ?? "none"}:${syncResult?.imported_case_ids.length ?? 0}:${writebackAuditSummary?.total_count ?? 0}:${mood}`,
    [larkSpreadsheetStatus, syncResult, writebackAuditSummary, mood]
  );
  const auditPreviewSignature = useMemo(
    () =>
      [
        activeWritebackAuditStatus ?? "all",
        writebackAuditSummary?.total_count ?? "none",
        writebackAuditSummary?.by_status.succeeded ?? 0,
        writebackAuditSummary?.by_status.failed ?? 0,
        writebackAuditSummary?.by_status.skipped ?? 0,
        writebackAuditList?.total_count ?? "none",
        ...(writebackAuditList?.audits.map((audit) => `${audit.job_id}:${audit.status}:${audit.updated_at}`) ?? [])
      ].join("|"),
    [activeWritebackAuditStatus, writebackAuditList, writebackAuditSummary]
  );
  const larkOperationAuditSignature = useMemo(
    () =>
      [
        activeLarkOperationAuditStatus ?? "all",
        larkOperationAuditList?.total_count ?? "none",
        ...(larkOperationAuditList?.audits.map((audit) => `${audit.audit_id}:${audit.status}:${audit.created_at}`) ?? [])
      ].join("|"),
    [activeLarkOperationAuditStatus, larkOperationAuditList]
  );

  useEffect(() => {
    setIsAuditPreviewOpen(hasWritebackAuditPreview);
  }, [auditPreviewSignature, hasWritebackAuditPreview]);

  useEffect(() => {
    setIsLarkOperationAuditOpen(hasLarkOperationAuditPreview);
  }, [hasLarkOperationAuditPreview, larkOperationAuditSignature]);

  useGSAP(
    () => {
      const panel = panelRef.current;
      if (!panel || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
        return;
      }
      gsap.from(panel.querySelectorAll(".writeback-stage-step"), {
        opacity: 0,
        y: 10,
        duration: 0.42,
        ease: "power2.out",
        stagger: 0.08
      });
      gsap.from(panel.querySelectorAll(".writeback-link-console, .writeback-rerun-capsule, .writeback-audit-orbit"), {
        opacity: 0,
        y: 18,
        rotateX: -4,
        duration: 0.58,
        ease: "power3.out",
        stagger: 0.09
      });
      gsap.to(panel.querySelectorAll(".writeback-worker"), {
        y: mood === "idle" ? -5 : -2,
        duration: mood === "idle" ? 1.1 : 0.6,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
        stagger: 0.13
      });
      gsap.to(panel.querySelectorAll(".writeback-crew-stage__package"), {
        x: mood === "idle" ? 28 : 82,
        duration: mood === "idle" ? 2.4 : 1.2,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true
      });
    },
    { dependencies: [resultSignature], scope: panelRef, revertOnUpdate: true }
  );

  function loadLarkOperationAudits(status: string | null) {
    setIsLarkOperationAuditOpen(true);
    onLoadLarkOperationAudits(status);
  }

  const auditPreviewDrawer =
    hasWritebackAuditPreview && isAuditPreviewOpen ? (
      <aside className="writeback-audit-drawer" aria-label="审计预览">
        <div className="writeback-audit-drawer__header">
          <div>
            <p className="writeback-panel-heading__eyebrow">审计预览</p>
            <h3>写回审计结果</h3>
            <p>当前筛选：{filterLabel(activeWritebackAuditStatus)}</p>
          </div>
          <div className="writeback-audit-drawer__actions">
            <button type="button" onClick={() => onLoadWritebackAudits(null)}>
              查看全部
            </button>
            <button type="button" aria-label="关闭审计预览" onClick={() => setIsAuditPreviewOpen(false)}>
              关闭
            </button>
          </div>
        </div>
        {writebackAuditSummary ? (
          <WritebackAuditSummary summary={writebackAuditSummary} onLoadStatus={onLoadWritebackAudits} />
        ) : null}
        {writebackAuditList ? (
          <WritebackAuditList
            audits={writebackAuditList.audits}
            activeFilter={activeWritebackAuditStatus}
            totalCount={writebackAuditList.total_count}
            writebackResult={writebackResult}
            onOpenJob={onOpenAuditJob}
            onRetry={onRetryAudit}
            onLoadMore={onLoadMoreWritebackAudits}
          />
        ) : null}
      </aside>
    ) : null;

  const larkOperationAuditDrawer =
    larkOperationAuditList && isLarkOperationAuditOpen ? (
      <aside className="writeback-audit-drawer" aria-label="Lark 操作审计">
        <div className="writeback-audit-drawer__header">
          <div>
            <p className="writeback-panel-heading__eyebrow">连接审计</p>
            <h3>Lark CLI 操作记录</h3>
            <p>记录连接检查、同步和写回的实际 CLI 操作、耗时和权限修复线索。</p>
          </div>
          <div className="writeback-audit-drawer__actions">
            <button type="button" onClick={() => loadLarkOperationAudits(null)}>
              查看全部
            </button>
            <button type="button" aria-label="关闭 Lark 操作审计" onClick={() => setIsLarkOperationAuditOpen(false)}>
              关闭
            </button>
          </div>
        </div>
        <LarkOperationAuditList
          audits={larkOperationAuditList.audits}
          totalCount={larkOperationAuditList.total_count}
          activeFilter={activeLarkOperationAuditStatus}
          onLoadStatus={loadLarkOperationAudits}
          onLoadMore={onLoadMoreLarkOperationAudits}
        />
      </aside>
    ) : null;

  return (
    <ProductSurface
      title="飞书表格同步"
      eyebrow="数据回写"
      description="从飞书表格拉取样本、按行重跑 debug、生成闭环报告，并把结果写回原表。"
      className="spreadsheet-operations"
    >
      <section ref={panelRef} className="writeback-command-center" aria-label="回写同步操作舱">
        <WritebackCrewStage
          mood={mood}
          importedCount={syncResult?.imported_case_ids.length ?? 0}
          failedAuditCount={failedAuditCount}
        />
        <div className="writeback-stage-line" aria-label="回写同步阶段">
          {["连接", "同步", "重跑", "审计"].map((label) => (
            <span className="writeback-stage-step" key={label}>
              {label}
            </span>
          ))}
        </div>
        <SpreadsheetControlsPanel
          spreadsheetUrl={spreadsheetUrl}
          spreadsheetId={spreadsheetId}
          sheetId={sheetId}
          rerunRowIds={rerunRowIds}
          rerunAutoClosure={rerunAutoClosure}
          rerunWriteback={rerunWriteback}
          onSpreadsheetUrlChange={onSpreadsheetUrlChange}
          onSpreadsheetIdChange={onSpreadsheetIdChange}
          onSheetIdChange={onSheetIdChange}
          onRerunRowIdsChange={onRerunRowIdsChange}
          onRerunAutoClosureChange={onRerunAutoClosureChange}
          onRerunWritebackChange={onRerunWritebackChange}
          onUseSpreadsheetUrl={onUseSpreadsheetUrl}
          onCheckLarkStatus={onCheckLarkStatus}
          onSyncSpreadsheet={onSyncSpreadsheet}
          onRerunSpreadsheetRows={onRerunSpreadsheetRows}
          onLoadWritebackAuditSummary={onLoadWritebackAuditSummary}
          onLoadWritebackAudits={onLoadWritebackAudits}
        />
        <div className="writeback-result-stream">
          {larkSpreadsheetStatus ? <LarkSpreadsheetStatusPanel status={larkSpreadsheetStatus} /> : null}
          {larkSpreadsheetStatus ? (
            <div className="writeback-action-cluster" aria-label="Lark 操作审计控制">
              <button type="button" onClick={() => loadLarkOperationAudits(null)}>
                查看 Lark 操作审计
              </button>
              <button type="button" onClick={() => loadLarkOperationAudits("failed")}>
                查看失败 Lark 操作
              </button>
              <button type="button" onClick={onCheckLarkScopes}>
                检查 Lark 权限需求
              </button>
            </div>
          ) : null}
          {larkScopeCheck ? <LarkScopeRepairPanel scopeCheck={larkScopeCheck} /> : null}
          {larkSpreadsheetStatus || larkAuthSession ? (
            <LarkAuthSessionPanel
              authSession={larkAuthSession}
              onCreateAuthSession={onCreateLarkAuthSession}
              onCompleteAuthSession={onCompleteLarkAuthSession}
            />
          ) : null}
          {batchExportHref ? (
            <a className="download-link" href={batchExportHref} download="debug-agent-spreadsheet-batch.zip">
              下载本次飞书任务包
            </a>
          ) : null}
          {syncResult ? <SpreadsheetSyncResultPanel result={syncResult} /> : null}
        </div>
        {auditPreviewDrawer ? createPortal(auditPreviewDrawer, document.body) : null}
        {larkOperationAuditDrawer ? createPortal(larkOperationAuditDrawer, document.body) : null}
      </section>
    </ProductSurface>
  );
}

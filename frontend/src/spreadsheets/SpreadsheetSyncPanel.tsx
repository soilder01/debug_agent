import type {
  LarkSpreadsheetStatus,
  SpreadsheetSyncResponse,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackAuditCounts,
  SpreadsheetWritebackAuditListResponse,
  SpreadsheetWritebackResult
} from "../api/client";
import { ProductSurface } from "../ui/ProductPrimitives";
import { LarkSpreadsheetStatusPanel } from "./LarkSpreadsheetStatusPanel";
import { SpreadsheetControlsPanel } from "./SpreadsheetControlsPanel";
import { SpreadsheetSyncResultPanel } from "./SpreadsheetSyncResultPanel";
import { WritebackAuditList } from "./WritebackAuditList";
import { WritebackAuditSummary } from "./WritebackAuditSummary";

type SpreadsheetSyncPanelProps = {
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  larkSpreadsheetStatus: LarkSpreadsheetStatus | null;
  syncResult: SpreadsheetSyncResponse | null;
  writebackAuditSummary: SpreadsheetWritebackAuditCounts | null;
  writebackAuditList: SpreadsheetWritebackAuditListResponse | null;
  activeWritebackAuditStatus: string | null;
  writebackResult: SpreadsheetWritebackResult | null;
  onSpreadsheetUrlChange: (value: string) => void;
  onSpreadsheetIdChange: (value: string) => void;
  onSheetIdChange: (value: string) => void;
  onUseSpreadsheetUrl: () => void;
  onCheckLarkStatus: () => void;
  onSyncSpreadsheet: () => void;
  onLoadWritebackAuditSummary: () => void;
  onLoadWritebackAudits: (status: string | null) => void;
  onOpenAuditJob: (jobId: string) => void;
  onRetryAudit: (audit: SpreadsheetWritebackAudit) => void;
  onLoadMoreWritebackAudits: () => void;
};

export function SpreadsheetSyncPanel({
  spreadsheetUrl,
  spreadsheetId,
  sheetId,
  larkSpreadsheetStatus,
  syncResult,
  writebackAuditSummary,
  writebackAuditList,
  activeWritebackAuditStatus,
  writebackResult,
  onSpreadsheetUrlChange,
  onSpreadsheetIdChange,
  onSheetIdChange,
  onUseSpreadsheetUrl,
  onCheckLarkStatus,
  onSyncSpreadsheet,
  onLoadWritebackAuditSummary,
  onLoadWritebackAudits,
  onOpenAuditJob,
  onRetryAudit,
  onLoadMoreWritebackAudits
}: SpreadsheetSyncPanelProps) {
  return (
    <ProductSurface
      title="Spreadsheet Sync"
      eyebrow="Writeback"
      description="Sync Lark rows, inspect writeback audit health, and retry failed spreadsheet updates."
      className="spreadsheet-operations"
    >
      <SpreadsheetControlsPanel
        spreadsheetUrl={spreadsheetUrl}
        spreadsheetId={spreadsheetId}
        sheetId={sheetId}
        onSpreadsheetUrlChange={onSpreadsheetUrlChange}
        onSpreadsheetIdChange={onSpreadsheetIdChange}
        onSheetIdChange={onSheetIdChange}
        onUseSpreadsheetUrl={onUseSpreadsheetUrl}
        onCheckLarkStatus={onCheckLarkStatus}
        onSyncSpreadsheet={onSyncSpreadsheet}
        onLoadWritebackAuditSummary={onLoadWritebackAuditSummary}
        onLoadWritebackAudits={onLoadWritebackAudits}
      />
      {larkSpreadsheetStatus ? <LarkSpreadsheetStatusPanel status={larkSpreadsheetStatus} /> : null}
      {syncResult ? <SpreadsheetSyncResultPanel result={syncResult} /> : null}
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
    </ProductSurface>
  );
}

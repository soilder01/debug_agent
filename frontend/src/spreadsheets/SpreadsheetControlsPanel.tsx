type SpreadsheetControlsPanelProps = {
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  rerunRowIds: string;
  rerunAutoClosure: boolean;
  rerunWriteback: boolean;
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
};

export function SpreadsheetControlsPanel({
  spreadsheetUrl,
  spreadsheetId,
  sheetId,
  rerunRowIds,
  rerunAutoClosure,
  rerunWriteback,
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
  onLoadWritebackAudits
}: SpreadsheetControlsPanelProps) {
  return (
    <div className="writeback-control-deck">
      <section className="writeback-link-console" aria-label="飞书链接控制台">
        <div className="writeback-panel-heading">
          <p className="writeback-panel-heading__eyebrow">连接源</p>
          <h3>粘贴飞书表格链接</h3>
          <p>解析 token 和 sheet 后先检查连接，再同步或重跑指定行。</p>
        </div>
        <label htmlFor="lark-spreadsheet-url">飞书表格链接</label>
        <input
          aria-label="飞书表格链接"
          id="lark-spreadsheet-url"
          value={spreadsheetUrl}
          onChange={(event) => onSpreadsheetUrlChange(event.target.value)}
        />
        <div className="writeback-token-row">
          <label htmlFor="spreadsheet-id">表格 Token</label>
          <input
            aria-label="表格 Token"
            id="spreadsheet-id"
            value={spreadsheetId}
            onChange={(event) => onSpreadsheetIdChange(event.target.value)}
          />
          <label htmlFor="sheet-id">工作表 ID</label>
          <input aria-label="工作表 ID" id="sheet-id" value={sheetId} onChange={(event) => onSheetIdChange(event.target.value)} />
        </div>
        <div className="writeback-action-cluster">
          <button aria-label="解析飞书表格链接" className="writeback-button writeback-button--ghost" type="button" onClick={onUseSpreadsheetUrl}>
            解析链接
          </button>
          <button aria-label="检查飞书连接" className="writeback-button writeback-button--pulse" type="button" onClick={onCheckLarkStatus}>
            检查连接
          </button>
          <button aria-label="同步表格行" className="writeback-button writeback-button--primary" type="button" onClick={onSyncSpreadsheet}>
            同步表格
          </button>
        </div>
      </section>

      <section className="writeback-rerun-capsule" aria-label="重跑任务舱">
        <div className="writeback-panel-heading">
          <p className="writeback-panel-heading__eyebrow">重跑闭环</p>
          <h3>选择行号并自动推进 Debug</h3>
          <p>支持单行、逗号列表和范围，例如 3、2,4,8 或 2-8。</p>
        </div>
        <label htmlFor="spreadsheet-rerun-row-ids">重跑行号</label>
        <input
          aria-label="重跑行号"
          id="spreadsheet-rerun-row-ids"
          value={rerunRowIds}
          placeholder="例如：2,3,4 或 2-8"
          onChange={(event) => onRerunRowIdsChange(event.target.value)}
        />
        <div className="writeback-toggle-row">
          <label className="writeback-toggle" htmlFor="spreadsheet-rerun-auto-closure">
            <input
              aria-label="启用自动闭环"
              id="spreadsheet-rerun-auto-closure"
              type="checkbox"
              checked={rerunAutoClosure}
              onChange={(event) => onRerunAutoClosureChange(event.target.checked)}
            />
            <span>自动闭环</span>
          </label>
          <label className="writeback-toggle" htmlFor="spreadsheet-rerun-writeback">
            <input
              aria-label="写回重跑结果"
              id="spreadsheet-rerun-writeback"
              type="checkbox"
              checked={rerunWriteback}
              onChange={(event) => onRerunWritebackChange(event.target.checked)}
            />
            <span>写回结果</span>
          </label>
        </div>
        <button
          aria-label="重跑选中表格行"
          className="writeback-button writeback-button--launch"
          type="button"
          onClick={onRerunSpreadsheetRows}
        >
          重跑选中行
        </button>
      </section>

      <section className="writeback-audit-orbit" aria-label="回写审计控制台">
        <div className="writeback-panel-heading">
          <p className="writeback-panel-heading__eyebrow">审计记录</p>
          <h3>查看写回结果和失败重试</h3>
        </div>
        <button aria-label="加载审计概览" className="writeback-button writeback-button--ghost" type="button" onClick={onLoadWritebackAuditSummary}>
          加载审计概览
        </button>
        <div className="writeback-audit-filters">
          <button aria-label="加载全部审计" type="button" onClick={() => onLoadWritebackAudits(null)}>
            全部
          </button>
          <button aria-label="加载成功审计" type="button" onClick={() => onLoadWritebackAudits("succeeded")}>
            成功
          </button>
          <button aria-label="加载失败审计" type="button" onClick={() => onLoadWritebackAudits("failed")}>
            失败
          </button>
          <button aria-label="加载跳过审计" type="button" onClick={() => onLoadWritebackAudits("skipped")}>
            跳过
          </button>
        </div>
      </section>
    </div>
  );
}

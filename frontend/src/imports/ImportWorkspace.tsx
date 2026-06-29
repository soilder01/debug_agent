import type { CsvImportResponse, JsonlImportResponse, SpreadsheetRowImportResponse } from "../api/client";
import { SpreadsheetImportPanel } from "../spreadsheets/SpreadsheetImportPanel";
import { EmptyState, ProductSurface } from "../ui/ProductPrimitives";
import { CSVImportPanel } from "./CSVImportPanel";
import { JSONLImportPanel } from "./JSONLImportPanel";

type ImportWorkspaceProps = {
  jsonlCases: string;
  jsonlImportResult: JsonlImportResponse | null;
  csvCases: string;
  csvImportResult: CsvImportResponse | null;
  spreadsheetRowsJson: string;
  spreadsheetImportResult: SpreadsheetRowImportResponse | null;
  onJsonlChange: (value: string) => void;
  onCsvChange: (value: string) => void;
  onSpreadsheetRowsJsonChange: (value: string) => void;
  onImportJsonl: () => void;
  onImportCsv: () => void;
  onImportSpreadsheetRowsJson: () => void;
};

export function ImportWorkspace({
  jsonlCases,
  jsonlImportResult,
  csvCases,
  csvImportResult,
  spreadsheetRowsJson,
  spreadsheetImportResult,
  onJsonlChange,
  onCsvChange,
  onSpreadsheetRowsJsonChange,
  onImportJsonl,
  onImportCsv,
  onImportSpreadsheetRowsJson
}: ImportWorkspaceProps) {
  return (
    <div className="intake-stack intake-command-center" aria-label="样本导入方式">
      <section className="intake-route-board" aria-label="数据导入路线">
        <div>
          <p className="intake-route-board__eyebrow">先选来源</p>
          <h2>不知道用哪个导入？按数据来源选</h2>
          <p>
            导入会把外部 badcase 变成本地样本 case_id。导入成功后，到“调查工作台”用这些 case_id 批量提交 debug。
          </p>
        </div>
        <div className="intake-route-board__cards" aria-label="导入方式说明">
          <article className="intake-route-card" data-route-accent="blue">
            <span>JSONL</span>
            <strong>工程/脚本产物</strong>
            <p>一行一个 JSON，适合 harness、离线采集或程序批量导出的样本。</p>
          </article>
          <article className="intake-route-card" data-route-accent="green">
            <span>CSV</span>
            <strong>人工整理表格</strong>
            <p>适合评测同学从 Excel/表格导出的 badcase 批次。</p>
          </article>
          <article className="intake-route-card" data-route-accent="purple">
            <span>飞书行 JSON</span>
            <strong>同步后的结构化行</strong>
            <p>已经有飞书链接时，优先去“回写同步”直接同步；这里用于粘贴导出的行 JSON。</p>
          </article>
        </div>
      </section>
      <ProductSurface
        title="JSONL 样本包"
        eyebrow="数据导入"
        description="适合工程链路或脚本导出的 badcase：一行一个 JSON，导入后生成可调试的 case_id。"
        className="import-panel import-panel--jsonl"
      >
        <JSONLImportPanel
          value={jsonlCases}
          result={jsonlImportResult}
          onChange={onJsonlChange}
          onImport={onImportJsonl}
        />
        {jsonlImportResult ? null : <EmptyState title="等待 JSONL 导入" description="粘贴 JSONL 后点击导入，这里会显示成功样本和被拒绝的行。" />}
      </ProductSurface>
      <ProductSurface
        title="CSV 表格批次"
        eyebrow="数据导入"
        description="适合人工整理后的表格批次：保留表头，按行导入 case_id、图片/视频、prompt、标答和预测。"
        className="import-panel import-panel--csv"
      >
        <CSVImportPanel value={csvCases} result={csvImportResult} onChange={onCsvChange} onImport={onImportCsv} />
        {csvImportResult ? null : <EmptyState title="等待 CSV 导入" description="粘贴 CSV 后点击导入，系统会告诉你哪些样本可进入调查工作台。" />}
      </ProductSurface>
      <ProductSurface
        title="飞书行 JSON"
        eyebrow="数据导入"
        description="适合已经拿到飞书行 JSON 的场景。只有飞书链接时，建议先去“回写同步”让系统自动读取。"
        className="import-panel import-panel--spreadsheet"
      >
        <SpreadsheetImportPanel
          value={spreadsheetRowsJson}
          result={spreadsheetImportResult}
          onChange={onSpreadsheetRowsJsonChange}
          onImport={onImportSpreadsheetRowsJson}
        />
        {spreadsheetImportResult ? null : (
          <EmptyState title="等待飞书行导入" description="粘贴 rows JSON 后点击导入；若你只有飞书表格链接，请切到回写同步。" />
        )}
      </ProductSurface>
    </div>
  );
}

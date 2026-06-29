import type { SpreadsheetRowImportResponse } from "../api/client";
import { SpreadsheetImportResultPanel } from "./SpreadsheetImportResultPanel";

type SpreadsheetImportPanelProps = {
  value: string;
  result: SpreadsheetRowImportResponse | null;
  onChange: (value: string) => void;
  onImport: () => void;
};

export function SpreadsheetImportPanel({ value, result, onChange, onImport }: SpreadsheetImportPanelProps) {
  return (
    <>
      <label htmlFor="spreadsheet-rows-json">飞书行 JSON</label>
      <p className="import-panel__hint">这里粘贴的是已经导出的 rows JSON。只有飞书链接时，不要手动贴，去“回写同步”自动读取。</p>
      <textarea
        id="spreadsheet-rows-json"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={'[{"sheet_row_id":"7","case_id":"JSZN-096","image_uri":"file://..."}]'}
      />
      <button type="button" aria-label="导入飞书行 JSON" onClick={onImport}>
        导入飞书行 JSON
      </button>
      {result ? <SpreadsheetImportResultPanel result={result} /> : null}
    </>
  );
}

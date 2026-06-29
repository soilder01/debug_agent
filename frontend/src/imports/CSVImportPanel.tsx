import type { CsvImportResponse } from "../api/client";
import { CSVImportResultPanel } from "./CSVImportResultPanel";

type CSVImportPanelProps = {
  value: string;
  result: CsvImportResponse | null;
  onChange: (value: string) => void;
  onImport: () => void;
};

export function CSVImportPanel({ value, result, onChange, onImport }: CSVImportPanelProps) {
  return (
    <>
      <label htmlFor="csv-cases">CSV 案件数据</label>
      <p className="import-panel__hint">适合从 Excel 或表格复制出的批次。第一行必须是表头，后面每行是一个样本。</p>
      <textarea
        id="csv-cases"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={"case_id,image_uri,prompt,expected_output_json\nJSZN-096,file://video.mp4,请判断视频内容,\"[...]\""}
      />
      <button type="button" aria-label="导入 CSV 案件" onClick={onImport}>
        导入 CSV 案件
      </button>
      {result ? <CSVImportResultPanel result={result} /> : null}
    </>
  );
}

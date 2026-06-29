import type { JsonlImportResponse } from "../api/client";
import { JSONLImportResultPanel } from "./JSONLImportResultPanel";

type JSONLImportPanelProps = {
  value: string;
  result: JsonlImportResponse | null;
  onChange: (value: string) => void;
  onImport: () => void;
};

export function JSONLImportPanel({ value, result, onChange, onImport }: JSONLImportPanelProps) {
  return (
    <>
      <label htmlFor="jsonl-cases">JSONL 案件数据</label>
      <p className="import-panel__hint">一行一个样本 JSON。导入成功后，样本 ID 会出现在下方结果里，可直接拿去调查工作台批量调试。</p>
      <textarea
        id="jsonl-cases"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={"{\"case_id\":\"JSZN-096\",\"image_uri\":\"file://...\",\"prompt\":\"...\"}\n{\"case_id\":\"JSZN-049\",\"image_uri\":\"file://...\",\"prompt\":\"...\"}"}
      />
      <button type="button" aria-label="导入 JSONL 案件" onClick={onImport}>
        导入 JSONL 案件
      </button>
      {result ? <JSONLImportResultPanel result={result} /> : null}
    </>
  );
}

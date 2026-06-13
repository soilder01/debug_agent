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
      <label htmlFor="jsonl-cases">JSONL cases</label>
      <textarea id="jsonl-cases" value={value} onChange={(event) => onChange(event.target.value)} />
      <button type="button" onClick={onImport}>
        Import JSONL cases
      </button>
      {result ? <JSONLImportResultPanel result={result} /> : null}
    </>
  );
}

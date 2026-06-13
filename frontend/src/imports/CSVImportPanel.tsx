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
      <label htmlFor="csv-cases">CSV cases</label>
      <textarea id="csv-cases" value={value} onChange={(event) => onChange(event.target.value)} />
      <button type="button" onClick={onImport}>
        Import CSV cases
      </button>
      {result ? <CSVImportResultPanel result={result} /> : null}
    </>
  );
}

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
      <label htmlFor="spreadsheet-rows-json">Spreadsheet rows JSON</label>
      <textarea id="spreadsheet-rows-json" value={value} onChange={(event) => onChange(event.target.value)} />
      <button type="button" onClick={onImport}>
        Import spreadsheet rows JSON
      </button>
      {result ? <SpreadsheetImportResultPanel result={result} /> : null}
    </>
  );
}

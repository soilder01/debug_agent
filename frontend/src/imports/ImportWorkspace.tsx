import type { CsvImportResponse, JsonlImportResponse, SpreadsheetRowImportResponse } from "../api/client";
import { SpreadsheetImportPanel } from "../spreadsheets/SpreadsheetImportPanel";
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
    <>
      <section>
        <h2>JSONL Import</h2>
        <JSONLImportPanel
          value={jsonlCases}
          result={jsonlImportResult}
          onChange={onJsonlChange}
          onImport={onImportJsonl}
        />
      </section>
      <section>
        <h2>CSV Import</h2>
        <CSVImportPanel value={csvCases} result={csvImportResult} onChange={onCsvChange} onImport={onImportCsv} />
      </section>
      <section>
        <h2>Spreadsheet Rows Import</h2>
        <SpreadsheetImportPanel
          value={spreadsheetRowsJson}
          result={spreadsheetImportResult}
          onChange={onSpreadsheetRowsJsonChange}
          onImport={onImportSpreadsheetRowsJson}
        />
      </section>
    </>
  );
}

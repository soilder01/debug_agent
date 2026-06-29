import type {
  JsonlImportResponse,
  CsvImportResponse,
  SpreadsheetRowImportResponse
} from "./types";

export async function importJsonlCases(jsonl: string, createJobs = true): Promise<JsonlImportResponse> {
  const response = await fetch("/api/imports/jsonl", {
    body: JSON.stringify({ jsonl, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`导入 JSONL 样本失败：${response.status}`);
  }
  return (await response.json()) as JsonlImportResponse;
}


export async function importCsvCases(csvText: string, createJobs = true): Promise<CsvImportResponse> {
  const response = await fetch("/api/imports/csv", {
    body: JSON.stringify({ csv_text: csvText, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`导入 CSV 样本失败：${response.status}`);
  }
  return (await response.json()) as CsvImportResponse;
}


export async function importSpreadsheetRows(
  rows: Array<Record<string, unknown>>,
  createJobs = true
): Promise<SpreadsheetRowImportResponse> {
  const response = await fetch("/api/imports/spreadsheet-rows", {
    body: JSON.stringify({ rows, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`导入飞书行失败：${response.status}`);
  }
  return (await response.json()) as SpreadsheetRowImportResponse;
}

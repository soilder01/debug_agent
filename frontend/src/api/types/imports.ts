import type { SubmittedDebugJob } from "./debug";

export type JsonlRejectedLine = {
  line_number: number;
  error_message: string;
};

export type JsonlImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_lines: JsonlRejectedLine[];
};

export type CsvRejectedRow = {
  row_number: number;
  error_message: string;
};

export type CsvImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_rows: CsvRejectedRow[];
};

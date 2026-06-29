import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CsvImportResponse, JsonlImportResponse, SpreadsheetRowImportResponse } from "../api/client";
import { ImportWorkspace } from "./ImportWorkspace";

function makeJsonlResult(): JsonlImportResponse {
  return {
    imported_case_ids: ["case-jsonl-1"],
    jobs: [],
    rejected_lines: []
  };
}

function makeCsvResult(): CsvImportResponse {
  return {
    imported_case_ids: ["case-csv-1"],
    jobs: [],
    rejected_rows: []
  };
}

function makeSpreadsheetResult(): SpreadsheetRowImportResponse {
  return {
    imported_case_ids: ["case-sheet-1"],
    imported_rows: [{ sheet_row_id: "7", case_id: "case-sheet-1" }],
    jobs: [],
    rejected_rows: []
  };
}

describe("ImportWorkspace", () => {
  it("renders productized intake surfaces with helper copy and empty states", () => {
    render(
      <ImportWorkspace
        jsonlCases=""
        jsonlImportResult={null}
        csvCases=""
        csvImportResult={null}
        spreadsheetRowsJson=""
        spreadsheetImportResult={null}
        onJsonlChange={vi.fn()}
        onCsvChange={vi.fn()}
        onSpreadsheetRowsJsonChange={vi.fn()}
        onImportJsonl={vi.fn()}
        onImportCsv={vi.fn()}
        onImportSpreadsheetRowsJson={vi.fn()}
      />
    );

    expect(screen.getByLabelText("样本导入方式")).toHaveClass("intake-command-center");
    expect(screen.getByRole("region", { name: "数据导入路线" })).toHaveClass("intake-route-board");
    expect(screen.getByRole("heading", { name: "不知道用哪个导入？按数据来源选" })).toBeInTheDocument();
    expect(screen.getByText("导入会把外部 badcase 变成本地样本 case_id。导入成功后，到“调查工作台”用这些 case_id 批量提交 debug。")).toBeInTheDocument();
    expect(screen.getByText("工程/脚本产物")).toBeInTheDocument();
    expect(screen.getByText("人工整理表格")).toBeInTheDocument();
    expect(screen.getByText("同步后的结构化行")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "JSONL 样本包" })).toHaveClass("import-panel--jsonl");
    expect(screen.getByRole("region", { name: "CSV 表格批次" })).toHaveClass("import-panel--csv");
    expect(screen.getByRole("region", { name: "飞书行 JSON" })).toHaveClass("import-panel--spreadsheet");
    expect(screen.getAllByText(/等待.*导入/).length).toBe(3);
  });

  it("renders import sections, result summaries, and delegates actions", async () => {
    const onJsonlChange = vi.fn();
    const onCsvChange = vi.fn();
    const onSpreadsheetRowsJsonChange = vi.fn();
    const onImportJsonl = vi.fn();
    const onImportCsv = vi.fn();
    const onImportSpreadsheetRowsJson = vi.fn();

    render(
      <ImportWorkspace
        jsonlCases="{}"
        jsonlImportResult={makeJsonlResult()}
        csvCases="case_id,prompt"
        csvImportResult={makeCsvResult()}
        spreadsheetRowsJson="[]"
        spreadsheetImportResult={makeSpreadsheetResult()}
        onJsonlChange={onJsonlChange}
        onCsvChange={onCsvChange}
        onSpreadsheetRowsJsonChange={onSpreadsheetRowsJsonChange}
        onImportJsonl={onImportJsonl}
        onImportCsv={onImportCsv}
        onImportSpreadsheetRowsJson={onImportSpreadsheetRowsJson}
      />
    );

    expect(screen.getByRole("heading", { name: "JSONL 样本包" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CSV 表格批次" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "飞书行 JSON" })).toBeInTheDocument();
    expect(screen.getByText("一行一个样本 JSON。导入成功后，样本 ID 会出现在下方结果里，可直接拿去调查工作台批量调试。")).toBeInTheDocument();
    expect(screen.getByText("适合从 Excel 或表格复制出的批次。第一行必须是表头，后面每行是一个样本。")).toBeInTheDocument();
    expect(screen.getByText("这里粘贴的是已经导出的 rows JSON。只有飞书链接时，不要手动贴，去“回写同步”自动读取。")).toBeInTheDocument();
    expect(screen.getByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("表格导入样本：1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("JSONL 案件数据"), { target: { value: "{\"case_id\":\"case-2\"}" } });
    fireEvent.change(screen.getByLabelText("CSV 案件数据"), { target: { value: "case_id\ncase-2" } });
    fireEvent.change(screen.getByRole("textbox", { name: "飞书行 JSON" }), { target: { value: "[{}]" } });
    await userEvent.click(screen.getByRole("button", { name: "导入 JSONL 案件" }));
    await userEvent.click(screen.getByRole("button", { name: "导入 CSV 案件" }));
    await userEvent.click(screen.getByRole("button", { name: "导入飞书行 JSON" }));

    expect(onJsonlChange).toHaveBeenCalledWith("{\"case_id\":\"case-2\"}");
    expect(onCsvChange).toHaveBeenCalledWith("case_id\ncase-2");
    expect(onSpreadsheetRowsJsonChange).toHaveBeenCalledWith("[{}]");
    expect(onImportJsonl).toHaveBeenCalledTimes(1);
    expect(onImportCsv).toHaveBeenCalledTimes(1);
    expect(onImportSpreadsheetRowsJson).toHaveBeenCalledTimes(1);
  });
});

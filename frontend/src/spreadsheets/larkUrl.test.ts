import { describe, expect, it } from "vitest";

import { parseLarkSpreadsheetUrl } from "./larkUrl";

describe("parseLarkSpreadsheetUrl", () => {
  it("parses spreadsheet and sheet identifiers from a Lark spreadsheet URL", () => {
    expect(
      parseLarkSpreadsheetUrl("https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123")
    ).toEqual({
      spreadsheetId: "testSpreadsheetToken123",
      sheetId: "testSheet123"
    });
  });

  it("rejects URLs without a sheets path", () => {
    expect(() => parseLarkSpreadsheetUrl("https://bytedance.larkoffice.com/docx/abc?sheet=testSheet123")).toThrow(
      "飞书表格链接必须包含 /sheets/{spreadsheet_id}"
    );
  });

  it("rejects URLs without a sheet query parameter", () => {
    expect(() => parseLarkSpreadsheetUrl("https://example.larkoffice.com/sheets/testSpreadsheetToken123")).toThrow(
      "飞书表格链接必须包含 sheet 查询参数"
    );
  });
});

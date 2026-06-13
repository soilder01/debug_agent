import { describe, expect, it } from "vitest";

import { parseLarkSpreadsheetUrl } from "./larkUrl";

describe("parseLarkSpreadsheetUrl", () => {
  it("parses spreadsheet and sheet identifiers from a Lark spreadsheet URL", () => {
    expect(
      parseLarkSpreadsheetUrl("https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX")
    ).toEqual({
      spreadsheetId: "NLews6C2ShValptV7IdcJ62tnWc",
      sheetId: "qJAomX"
    });
  });

  it("rejects URLs without a sheets path", () => {
    expect(() => parseLarkSpreadsheetUrl("https://bytedance.larkoffice.com/docx/abc?sheet=qJAomX")).toThrow(
      "Lark spreadsheet URL must contain /sheets/{spreadsheet_id}"
    );
  });

  it("rejects URLs without a sheet query parameter", () => {
    expect(() => parseLarkSpreadsheetUrl("https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc")).toThrow(
      "Lark spreadsheet URL must include a sheet query parameter"
    );
  });
});

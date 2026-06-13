export type LarkSpreadsheetUrlReference = {
  spreadsheetId: string;
  sheetId: string;
};

export function parseLarkSpreadsheetUrl(value: string): LarkSpreadsheetUrlReference {
  const parsed = new URL(value);
  const pathParts = parsed.pathname.split("/").filter(Boolean);
  if (pathParts.length < 2 || pathParts[0] !== "sheets") {
    throw new Error("Lark spreadsheet URL must contain /sheets/{spreadsheet_id}");
  }
  const sheetId = parsed.searchParams.get("sheet") ?? "";
  if (!sheetId) {
    throw new Error("Lark spreadsheet URL must include a sheet query parameter");
  }
  return { spreadsheetId: pathParts[1], sheetId };
}

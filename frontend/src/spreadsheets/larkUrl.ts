export type LarkSpreadsheetUrlReference = {
  spreadsheetId: string;
  sheetId: string;
};

export function parseLarkSpreadsheetUrl(value: string): LarkSpreadsheetUrlReference {
  const parsed = new URL(value);
  const pathParts = parsed.pathname.split("/").filter(Boolean);
  if (pathParts.length < 2 || pathParts[0] !== "sheets") {
    throw new Error("飞书表格链接必须包含 /sheets/{spreadsheet_id}");
  }
  const sheetId = parsed.searchParams.get("sheet") ?? "";
  if (!sheetId) {
    throw new Error("飞书表格链接必须包含 sheet 查询参数");
  }
  return { spreadsheetId: pathParts[1], sheetId };
}

export const jobListLimit = 50;
export const caseListLimit = 50;
export const defaultSpreadsheetUrl = "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123";
export const defaultSpreadsheetId = "testSpreadsheetToken123";
export const defaultSheetId = "testSheet123";
export const localDevActor = "local-dev-operator";

export function parseRerunRowIds(value: string): string[] {
  const rowIds: string[] = [];
  for (const token of value.split(/[,\s]+/).map((item) => item.trim()).filter(Boolean)) {
    const rangeMatch = token.match(/^(\d+)-(\d+)$/);
    if (rangeMatch) {
      const start = Number(rangeMatch[1]);
      const end = Number(rangeMatch[2]);
      for (let row = Math.min(start, end); row <= Math.max(start, end); row += 1) {
        rowIds.push(String(row));
      }
    } else {
      rowIds.push(token);
    }
  }
  return Array.from(new Set(rowIds));
}

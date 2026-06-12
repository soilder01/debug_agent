from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel


class LarkSpreadsheetReference(BaseModel):
    spreadsheet_id: str
    sheet_id: str


def parse_lark_spreadsheet_reference(value: str, sheet_id: str | None = None) -> LarkSpreadsheetReference:
    stripped_value = value.strip()
    if stripped_value.startswith(("http://", "https://")):
        return _parse_lark_sheet_url(stripped_value, sheet_id=sheet_id)
    resolved_sheet_id = _require_sheet_id(sheet_id)
    return LarkSpreadsheetReference(spreadsheet_id=stripped_value, sheet_id=resolved_sheet_id)


def _parse_lark_sheet_url(url: str, sheet_id: str | None) -> LarkSpreadsheetReference:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "sheets":
        raise ValueError("Lark spreadsheet URL must contain /sheets/{spreadsheet_id}")
    query_sheet_id = parse_qs(parsed.query).get("sheet", [""])[0]
    resolved_sheet_id = _require_sheet_id(sheet_id or query_sheet_id)
    return LarkSpreadsheetReference(spreadsheet_id=path_parts[1], sheet_id=resolved_sheet_id)


def _require_sheet_id(sheet_id: str | None) -> str:
    if sheet_id is None or sheet_id.strip() == "":
        raise ValueError("sheet_id is required for Lark spreadsheet references")
    return sheet_id.strip()

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

if TYPE_CHECKING:
    from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class LarkSpreadsheetReference(BaseModel):
    spreadsheet_id: str
    sheet_id: str


class LarkSheetsTransport(Protocol):
    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        """Read one sheet as a value matrix where the first row is the header."""

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        """Update one sheet row with field values."""


class LarkSpreadsheetClient:
    def __init__(self, transport: LarkSheetsTransport) -> None:
        self._transport = transport

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        from debug_agent.spreadsheets.sync import SpreadsheetSourceRow

        values = self._transport.read_values(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        if not values:
            return []
        headers = [str(header).strip() for header in values[0]]
        rows: list[SpreadsheetSourceRow] = []
        for row_number, row_values in enumerate(values[1:], start=2):
            if _is_empty_row(row_values):
                continue
            rows.append(
                SpreadsheetSourceRow(
                    row_id=str(row_number),
                    values={
                        header: value
                        for header, value in zip(headers, row_values, strict=False)
                        if header
                    },
                )
            )
        return rows

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self._transport.update_row(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id, row_id=row_id, fields=fields)


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


def _is_empty_row(values: list[object]) -> bool:
    return all(value is None or str(value).strip() == "" for value in values)

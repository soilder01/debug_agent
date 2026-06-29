from __future__ import annotations

import json
from time import perf_counter
from typing import TYPE_CHECKING, Protocol
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from debug_agent.lark.connector import (
    CommandRunner,
    LarkAuditSink,
    LarkCliConnector,
    LarkCliError,
    LarkConnectorProtocol,
    LarkConnectorStatus,
)
from debug_agent.telemetry.performance import record_performance_event

if TYPE_CHECKING:
    from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class LarkSpreadsheetReference(BaseModel):
    spreadsheet_id: str
    sheet_id: str


class LarkSheetsTransport(Protocol):
    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        """Read one sheet as a value matrix where the first row is the header."""

    def read_rows_json(self, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        """Read one sheet with row numbers and column letters when supported."""

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> dict[str, str] | None:
        """Update one sheet row with field values and return written fields when available."""


DEFAULT_LARK_CLI_TIMEOUT_SECONDS = 60


class LarkCliSheetsTransport:
    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        cli_command: str = "lark-cli",
        read_range: str = "A1:Z500",
        timeout_seconds: int = DEFAULT_LARK_CLI_TIMEOUT_SECONDS,
        profile: str = "",
        identity: str = "unknown",
        connector: LarkConnectorProtocol | None = None,
        audit_sink: LarkAuditSink | None = None,
    ) -> None:
        self._connector = connector or LarkCliConnector(
            command_runner=command_runner,
            cli_command=cli_command,
            timeout_seconds=timeout_seconds,
            profile=profile,
            identity=identity if identity in {"bot", "user", "unknown"} else "unknown",
            audit_sink=audit_sink,
        )
        self._read_range = read_range
        self._header_columns_cache: dict[tuple[str, str], dict[str, str]] = {}

    def connector_status(self) -> LarkConnectorStatus:
        return self._connector.status()

    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        data = self._read_rows_json(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        return _rows_json_to_matrix(data)

    def read_rows_json(self, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        return self._read_rows_json(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> dict[str, str]:
        started_at = perf_counter()
        header_columns = self._header_columns_for_sheet(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        written_fields: dict[str, str] = {}
        missing_fields: list[str] = []
        for field_name, field_value in fields.items():
            column = header_columns.get(field_name)
            if column is None:
                missing_fields.append(field_name)
                continue
            self._run_json_command(
                [
                    "sheets",
                    "+cells-set",
                    "--spreadsheet-token",
                    spreadsheet_id,
                    "--sheet-id",
                    sheet_id,
                    "--range",
                    f"{column}{row_id}",
                    "--cells",
                    "-",
                ],
                stdin=json.dumps([[{"value": field_value}]], ensure_ascii=False),
            )
            written_fields[field_name] = field_value
        if not written_fields:
            _record_writeback_field_resolution(
                started_at=started_at,
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                written_count=0,
                missing_count=len(missing_fields),
                status="failed",
            )
            missing_field_text = ", ".join(missing_fields) if missing_fields else "none"
            raise LarkCliError(f"Spreadsheet headers not found for any writeback fields: {missing_field_text}")
        _record_writeback_field_resolution(
            started_at=started_at,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            written_count=len(written_fields),
            missing_count=len(missing_fields),
        )
        return written_fields

    def _header_columns_for_sheet(self, *, spreadsheet_id: str, sheet_id: str) -> dict[str, str]:
        key = (spreadsheet_id, sheet_id)
        cached = self._header_columns_cache.get(key)
        if cached is not None:
            return cached
        data = self._read_rows_json(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        header_columns = _header_columns(data)
        self._header_columns_cache[key] = header_columns
        return header_columns

    def _read_rows_json(self, *, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        return self._run_json_command(
            [
                "sheets",
                "+csv-get",
                "--spreadsheet-token",
                spreadsheet_id,
                "--sheet-id",
                sheet_id,
                "--range",
                self._read_range,
                "--rows-json",
            ]
        )

    def _run_json_command(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        return self._connector.run_json(args, stdin=stdin)


class LarkSpreadsheetClient:
    def __init__(self, transport: LarkSheetsTransport) -> None:
        self._transport = transport

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        from debug_agent.spreadsheets.sync import SpreadsheetSourceRow

        read_rows_json = getattr(self._transport, "read_rows_json", None)
        if callable(read_rows_json):
            return _rows_json_to_source_rows(read_rows_json(spreadsheet_id, sheet_id))
        values = self._transport.read_values(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        header_index = _first_non_empty_row_index(values)
        if header_index is None:
            return []
        headers = [str(header).strip() for header in values[header_index]]
        rows: list[SpreadsheetSourceRow] = []
        for row_number, row_values in enumerate(values[header_index + 1 :], start=header_index + 2):
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

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> dict[str, str] | None:
        return self._transport.update_row(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id, row_id=row_id, fields=fields)

    def connector_status(self) -> LarkConnectorStatus:
        status_provider = getattr(self._transport, "connector_status", None)
        if callable(status_provider):
            return status_provider()
        return LarkConnectorStatus(mode="cli")


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


def _first_non_empty_row_index(rows: list[list[object]]) -> int | None:
    for index, values in enumerate(rows):
        if not _is_empty_row(values):
            return index
    return None


def _record_writeback_field_resolution(
    *,
    started_at: float,
    spreadsheet_id: str,
    sheet_id: str,
    written_count: int,
    missing_count: int,
    status: str = "succeeded",
) -> None:
    record_performance_event(
        component="lark_writeback",
        operation="resolve_fields",
        duration_ms=int((perf_counter() - started_at) * 1000),
        status=status,
        metadata={
            "spreadsheet_id": spreadsheet_id,
            "sheet_id": sheet_id,
            "written_count": written_count,
            "missing_count": missing_count,
        },
    )

def _rows_json_to_matrix(data: dict[str, object]) -> list[list[object]]:
    rows = _rows_json_entries(data)
    column_names: set[str] = set()
    for _, values in rows:
        column_names.update(values)

    columns = sorted(column_names, key=_column_index)
    return [[values.get(column, "") for column in columns] for _, values in sorted(rows)]


def _rows_json_to_source_rows(data: dict[str, object]) -> list[SpreadsheetSourceRow]:
    from debug_agent.spreadsheets.sync import SpreadsheetSourceRow

    rows = _rows_json_entries(data)
    if not rows:
        return []
    sorted_rows = sorted(rows)
    header_entry = next(
        ((row_number, values) for row_number, values in sorted_rows if not _is_empty_row(list(values.values()))),
        None,
    )
    if header_entry is None:
        return []
    header_row_number, header_values = header_entry
    headers_by_column = {
        column: str(value).strip()
        for column, value in header_values.items()
        if str(value).strip()
    }
    rows_out: list[SpreadsheetSourceRow] = []
    for row_number, values in sorted_rows:
        if row_number <= header_row_number or _is_empty_row(list(values.values())):
            continue
        row_values = {
            header: values.get(column, "")
            for column, header in headers_by_column.items()
            if header
        }
        field_columns: dict[str, str] = {}
        for column, header in headers_by_column.items():
            field_columns.setdefault(header, column)
            normalized_header = _normalized_header(header)
            if normalized_header:
                field_columns.setdefault(normalized_header, column)
        row_values["__field_columns"] = field_columns
        rows_out.append(SpreadsheetSourceRow(row_id=str(row_number), values=row_values))
    return rows_out


def _header_columns(data: dict[str, object]) -> dict[str, str]:
    rows = _rows_json_entries(data)
    header_row = next((values for _, values in sorted(rows) if not _is_empty_row(list(values.values()))), None)
    if header_row is None:
        raise LarkCliError("Spreadsheet header row is empty")
    headers: dict[str, str] = {}
    for column, value in header_row.items():
        header = str(value).strip()
        if not header:
            continue
        headers.setdefault(header, column)
        normalized_header = _normalized_header(header)
        if normalized_header:
            headers.setdefault(normalized_header, column)
    return headers


def _normalized_header(value: str) -> str:
    return value.splitlines()[0].strip()


def _rows_json_entries(data: dict[str, object]) -> list[tuple[int, dict[str, object]]]:
    rows_raw = data.get("rows", [])
    if not isinstance(rows_raw, list):
        raise LarkCliError("lark-cli rows-json data must contain a rows list")

    rows: list[tuple[int, dict[str, object]]] = []
    for row_raw in rows_raw:
        if not isinstance(row_raw, dict):
            raise LarkCliError("lark-cli rows-json row must be an object")
        row_number = row_raw.get("row_number")
        values_raw = row_raw.get("values", {})
        if not isinstance(row_number, int) or not isinstance(values_raw, dict):
            raise LarkCliError("lark-cli rows-json row has invalid shape")
        values = {str(column): value for column, value in values_raw.items()}
        rows.append((row_number, values))
    return rows


def _column_index(column_name: str) -> int:
    index = 0
    for char in column_name.upper():
        if not char.isalpha():
            return 1_000_000
        index = index * 26 + ord(char) - ord("A") + 1
    return index

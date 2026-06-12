from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
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


CommandRunner = Callable[[list[str], str | None], str]
DEFAULT_LARK_CLI_TIMEOUT_SECONDS = 60


class LarkCliError(RuntimeError):
    """Raised when lark-cli output cannot be used by the transport."""


class LarkCliSheetsTransport:
    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        read_range: str = "A1:Z500",
        timeout_seconds: int = DEFAULT_LARK_CLI_TIMEOUT_SECONDS,
    ) -> None:
        self._command_runner = command_runner or _subprocess_lark_cli_runner(timeout_seconds)
        self._read_range = read_range

    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        data = self._read_rows_json(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        return _rows_json_to_matrix(data)

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        data = self._read_rows_json(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
        header_columns = _header_columns(data)
        for field_name, field_value in fields.items():
            column = header_columns.get(field_name)
            if column is None:
                raise LarkCliError(f"Spreadsheet header not found: {field_name}")
            self._run_json_command(
                [
                    "lark-cli",
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

    def _read_rows_json(self, *, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        return self._run_json_command(
            [
                "lark-cli",
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
        output = self._command_runner(args, stdin)
        return _parse_lark_cli_data(output)


class LarkSpreadsheetClient:
    def __init__(self, transport: LarkSheetsTransport) -> None:
        self._transport = transport

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        from debug_agent.spreadsheets.sync import SpreadsheetSourceRow

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


def _first_non_empty_row_index(rows: list[list[object]]) -> int | None:
    for index, values in enumerate(rows):
        if not _is_empty_row(values):
            return index
    return None


def _subprocess_lark_cli_runner(timeout_seconds: int) -> CommandRunner:
    def run(args: list[str], stdin: str | None = None) -> str:
        return _run_lark_cli(args=args, stdin=stdin, timeout_seconds=timeout_seconds)

    return run


def _run_lark_cli(
    args: list[str],
    stdin: str | None = None,
    timeout_seconds: int = DEFAULT_LARK_CLI_TIMEOUT_SECONDS,
) -> str:
    try:
        completed = subprocess.run(
            args,
            input=stdin,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise LarkCliError(f"lark-cli timed out after {timeout_seconds} seconds") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"lark-cli exited {completed.returncode}"
        raise LarkCliError(message)
    return completed.stdout


def _parse_lark_cli_data(output: str) -> dict[str, object]:
    try:
        envelope = json.loads(output)
    except json.JSONDecodeError as exc:
        raise LarkCliError("lark-cli returned invalid JSON") from exc
    if not isinstance(envelope, dict):
        raise LarkCliError("lark-cli returned a non-object envelope")
    if envelope.get("ok") is False:
        raise LarkCliError(str(envelope.get("error", "lark-cli command failed")))
    data = envelope.get("data", {})
    if not isinstance(data, dict):
        raise LarkCliError("lark-cli returned an invalid data envelope")
    return data


def _rows_json_to_matrix(data: dict[str, object]) -> list[list[object]]:
    rows = _rows_json_entries(data)
    column_names: set[str] = set()
    for _, values in rows:
        column_names.update(values)

    columns = sorted(column_names, key=_column_index)
    return [[values.get(column, "") for column in columns] for _, values in sorted(rows)]


def _header_columns(data: dict[str, object]) -> dict[str, str]:
    rows = _rows_json_entries(data)
    header_row = next((values for _, values in sorted(rows) if not _is_empty_row(list(values.values()))), None)
    if header_row is None:
        raise LarkCliError("Spreadsheet header row is empty")
    return {str(value).strip(): column for column, value in header_row.items() if str(value).strip()}


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

from __future__ import annotations

from collections.abc import Callable

from debug_agent.api.badcase_intake_parsers import (
    _clip_text,
    _input_source_requires_media_resolution,
    _lark_sheet_cell_attachment,
    _object_string,
)
from debug_agent.api.schemas import SpreadsheetRerunRequest
from debug_agent.imports.spreadsheet_rows import (
    canonical_spreadsheet_column_name,
    parse_spreadsheet_rows,
)
from debug_agent.lark.bot import LarkBotCommandAction
from debug_agent.lark.connector import LarkCliConnector
from debug_agent.spreadsheets.lark import LarkCliError, LarkSpreadsheetClient
from debug_agent.spreadsheets.sync import SpreadsheetClient, SpreadsheetSourceRow


class SpreadsheetRerunPreflightController:
    def __init__(
        self,
        *,
        spreadsheet_client: Callable[[], SpreadsheetClient | None],
        configure_clients_from_request: Callable[[SpreadsheetRerunRequest], None],
        request_from_action: Callable[[dict[str, object]], SpreadsheetRerunRequest],
        read_connector: Callable[[str], LarkCliConnector],
        lark_sheet_cell: Callable[..., dict[str, object]],
        download_lark_sheet_attachment: Callable[..., dict[str, object]],
    ) -> None:
        self._spreadsheet_client = spreadsheet_client
        self._configure_clients_from_request = configure_clients_from_request
        self._request_from_action = request_from_action
        self._read_connector = read_connector
        self._lark_sheet_cell = lark_sheet_cell
        self._download_lark_sheet_attachment = download_lark_sheet_attachment

    def attach_preflight(self, action: LarkBotCommandAction) -> None:
        if action.kind != "spreadsheet_rerun":
            return
        action.parameters["preflight"] = self.preflight(action)

    def preflight(self, action: LarkBotCommandAction) -> dict[str, object]:
        try:
            request = self._request_from_action(action.model_dump(mode="json"))
            self._configure_clients_from_request(request)
            spreadsheet_client = self._spreadsheet_client()
            if spreadsheet_client is None:
                return {"status": "failed", "error": "Spreadsheet sync client is not configured"}
            source_rows = spreadsheet_client.list_rows(
                spreadsheet_id=request.spreadsheet_id,
                sheet_id=request.sheet_id,
            )
            requested_row_ids = [str(row_id) for row_id in request.row_ids if str(row_id).strip()]
            requested_row_id_set = set(requested_row_ids)
            rows_to_check = (
                [row for row in source_rows if row.row_id in requested_row_id_set]
                if requested_row_id_set
                else source_rows
            )
            present_row_ids = [row.row_id for row in rows_to_check]
            missing_row_ids = [
                row_id for row_id in requested_row_ids if row_id not in set(present_row_ids)
            ]
            parse_result = parse_spreadsheet_rows(
                [self._source_row_values_with_id(row) for row in rows_to_check]
            )
            selected_case_ids = {case_id.strip() for case_id in request.case_ids if case_id.strip()}
            imported_rows = [
                row
                for row in parse_result.imported_rows
                if not selected_case_ids or row.case.case_id in selected_case_ids
            ]
            skipped_case_row_ids = [
                row.sheet_row_id
                for row in parse_result.imported_rows
                if selected_case_ids and row.case.case_id not in selected_case_ids
            ]
            return {
                "status": "ok",
                "requested_row_ids": requested_row_ids,
                "present_row_ids": present_row_ids,
                "missing_row_ids": missing_row_ids,
                "valid_row_ids": [row.sheet_row_id for row in imported_rows],
                "valid_case_ids": [row.case.case_id for row in imported_rows],
                "rejected_rows": [
                    {
                        "row_id": row.sheet_row_id,
                        "error": row.error_message,
                    }
                    for row in parse_result.rejected_rows
                ],
                "skipped_case_row_ids": skipped_case_row_ids,
                "requested_row_count": len(requested_row_ids),
                "present_row_count": len(present_row_ids),
                "valid_job_count": len(imported_rows),
                "rejected_row_count": len(parse_result.rejected_rows),
                "missing_row_count": len(missing_row_ids),
            }
        except Exception as exc:
            return {"status": "failed", "error": str(exc)[:500]}

    def row_media_resolver(
        self,
        request: SpreadsheetRerunRequest,
    ) -> Callable[[SpreadsheetSourceRow], SpreadsheetSourceRow] | None:
        if not isinstance(self._spreadsheet_client(), LarkSpreadsheetClient):
            return None
        connector = self._read_connector("spreadsheet-rerun")

        def resolve(row: SpreadsheetSourceRow) -> SpreadsheetSourceRow:
            values = dict(row.values)
            media_field = self._media_field(values)
            if media_field is None:
                return row
            header, input_source, source_column = media_field
            if not source_column:
                return row
            cell = self._lark_sheet_cell(
                connector=connector,
                spreadsheet_token=request.spreadsheet_id,
                sheet_id=request.sheet_id,
                column=source_column,
                row=row.row_id,
            )
            attachment = _lark_sheet_cell_attachment(cell)
            if not attachment:
                return row
            try:
                downloaded = self._download_lark_sheet_attachment(
                    connector=connector,
                    attachment=attachment,
                    fallback_name=input_source,
                )
            except LarkCliError as exc:
                values["__media_input_error"] = _clip_text(str(exc), 500)
                return SpreadsheetSourceRow(row_id=row.row_id, values=values)
            media_uri = _object_string(downloaded, "uri")
            if media_uri:
                values[header] = media_uri
                values["__media_input_status"] = {
                    **attachment,
                    **downloaded,
                    "status": "downloaded",
                    "cell": f"{source_column}{row.row_id}",
                }
                return SpreadsheetSourceRow(row_id=row.row_id, values=values)
            return row

        return resolve

    @staticmethod
    def _source_row_values_with_id(row: object) -> dict[str, object]:
        values = dict(getattr(row, "values", {}) or {})
        values.setdefault("sheet_row_id", str(getattr(row, "row_id", "")))
        return values

    @staticmethod
    def _media_field(values: dict[str, object]) -> tuple[str, str, str] | None:
        raw_field_columns = values.get("__field_columns")
        field_columns = raw_field_columns if isinstance(raw_field_columns, dict) else {}
        for header, value in values.items():
            if header.startswith("__"):
                continue
            canonical = canonical_spreadsheet_column_name(str(header))
            if canonical not in {"image_uri", "input_source"}:
                continue
            input_source = str(value).strip()
            if not _input_source_requires_media_resolution(input_source):
                continue
            source_column = str(field_columns.get(header) or "").strip()
            return header, input_source, source_column
        return None

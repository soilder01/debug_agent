from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from uuid import uuid4

from debug_agent.api.badcase_intake_parsers import (
    _badcase_context_needs_locator,
    _badcase_context_read_failed,
    _badcase_context_with_content,
    _badcase_fields_from_base_records,
    _badcase_fields_from_debug_case,
    _badcase_link_context,
    _clip_text,
    _debug_case_from_row_result,
    _extract_badcase_fields_from_text,
    _first_non_empty_lark_row_index,
    _input_source_requires_media_resolution,
    _lark_base_records,
    _lark_base_tables,
    _lark_data_text,
    _lark_rows_json_entries,
    _lark_sheet_attachment_download_failed,
    _lark_sheet_cell_attachment,
    _named_values_preview,
    _object_fields,
    _object_string,
    _sheet_row_import_next_action,
    _sheet_row_matches_target_label,
    _stringify_lark_cell,
)
from debug_agent.artifacts.layout import safe_path_fragment
from debug_agent.imports.schema_mapping import (
    SpreadsheetSchemaMappingAgent,
    SpreadsheetSchemaMappingResult,
)
from debug_agent.lark.connector import LarkCliConnector, LarkCliError


class LarkBadcaseLinkContextResolver:
    def __init__(
        self,
        *,
        read_identity: Callable[[], Literal["bot", "user", "unknown"]],
        read_connector: Callable[[str], LarkCliConnector],
        schema_mapping_agent: Callable[[], SpreadsheetSchemaMappingAgent],
        media_dir: Callable[[], Path],
    ) -> None:
        self._read_identity = read_identity
        self._read_connector = read_connector
        self._schema_mapping_agent = schema_mapping_agent
        self._media_dir = media_dir

    def badcase_link_contexts(
        self,
        links: list[str],
        *,
        resolve_content: bool = False,
        actor: str = "",
        target_label: str = "",
    ) -> list[dict[str, object]]:
        contexts: list[dict[str, object]] = []
        for link in links:
            context = _badcase_link_context(link)
            if context is not None:
                if (
                    target_label
                    and context.get("link_type") == "lark_sheet"
                    and not context.get("row_id")
                ):
                    context["target_label"] = target_label
                if resolve_content:
                    context = self.resolve_badcase_link_context_content(
                        context=context, actor=actor
                    )
                contexts.append(context)
        return contexts

    def resolve_badcase_link_context_content(
        self,
        *,
        context: dict[str, object],
        actor: str,
    ) -> dict[str, object]:
        link_type = _object_string(context, "link_type")
        try:
            if link_type in {"lark_doc", "lark_wiki"}:
                return self.resolve_lark_doc_context(context=context, actor=actor)
            if link_type == "lark_sheet":
                return self.resolve_lark_sheet_context(context=context, actor=actor)
            if link_type == "lark_base":
                return self.resolve_lark_base_context(context=context, actor=actor)
        except LarkCliError as exc:
            return _badcase_context_read_failed(context=context, exc=exc)
        if link_type.startswith("lark_"):
            enriched = dict(context)
            enriched["status"] = "reader_not_supported"
            enriched["next_action"] = "已识别资源类型，但当前版本还不能直接读取该资源内容。"
            return enriched
        return context

    def resolve_lark_doc_context(
        self,
        *,
        context: dict[str, object],
        actor: str,
    ) -> dict[str, object]:
        doc = _object_string(context, "url") or _object_string(context, "token")
        if not doc:
            return _badcase_context_needs_locator(
                context=context,
                next_action="文档链接缺少 token，无法读取正文。",
            )
        identity = self._read_identity()
        connector = self._read_connector(actor)
        data = connector.run_json(
            [
                "docs",
                "+fetch",
                "--api-version",
                "v2",
                "--doc",
                doc,
                "--doc-format",
                "markdown",
                "--detail",
                "simple",
                "--scope",
                "full",
                "--format",
                "json",
                "--as",
                identity,
            ]
        )
        text = _lark_data_text(data)
        fields = _extract_badcase_fields_from_text(text)
        return _badcase_context_with_content(
            context=context,
            fields=fields,
            preview=text,
            next_action="已读取文档正文并尝试提取 badcase 字段。",
        )

    def resolve_lark_sheet_context(
        self,
        *,
        context: dict[str, object],
        actor: str,
    ) -> dict[str, object]:
        token = _object_string(context, "token")
        sheet_id = _object_string(context, "sheet_id")
        if not token or not sheet_id:
            return _badcase_context_needs_locator(
                context=context,
                next_action="表格链接需要带 sheet 参数，才能读取并选择样本行。",
            )
        identity = self._read_identity()
        connector = self._read_connector(actor)
        data = connector.run_json(
            [
                "sheets",
                "+csv-get",
                "--spreadsheet-token",
                token,
                "--sheet-id",
                sheet_id,
                "--range",
                "A1:AZ50",
                "--rows-json",
                "--format",
                "json",
                "--as",
                identity,
            ]
        )
        row_result = self.debug_case_from_sheet_rows(
            data,
            preferred_row_id=_object_string(context, "row_id"),
            preferred_row_label=_object_string(context, "target_label"),
        )
        fields = _object_fields(row_result, "fields")
        media_input = self.resolve_lark_sheet_media_input(
            connector=connector,
            token=token,
            sheet_id=sheet_id,
            row_result=row_result,
            fields=fields,
        )
        debug_case = _debug_case_from_row_result(row_result)
        media_status = _object_string(media_input, "status")
        if debug_case is not None and media_input and fields.get("input_source"):
            debug_case = debug_case.model_copy(update={"image_uri": fields["input_source"]})
            row_result["debug_case"] = debug_case.model_dump(mode="json")
        if media_status in {"download_failed", "missing_attachment"}:
            row_result.pop("debug_case", None)
        enriched = self.sheet_row_context_with_import_result(
            context=context,
            row_result=row_result,
            fields=fields,
        )
        if media_input:
            enriched["media_input"] = media_input
            if media_status in {"download_failed", "missing_attachment"}:
                enriched["status"] = media_status
                enriched["next_action"] = _object_string(media_input, "next_action")
        selected_row = _object_string(row_result, "selected_row")
        if selected_row:
            enriched["selected_row"] = selected_row
        selected_label = _object_string(row_result, "selected_label")
        if selected_label:
            enriched["selected_label"] = selected_label
        row_count = row_result.get("row_count")
        if isinstance(row_count, int):
            enriched["row_count"] = row_count
        return enriched

    def resolve_lark_base_context(
        self,
        *,
        context: dict[str, object],
        actor: str,
    ) -> dict[str, object]:
        token = _object_string(context, "token")
        if not token:
            return _badcase_context_needs_locator(
                context=context,
                next_action="Base 链接缺少 token，无法读取记录。",
            )
        table_id = _object_string(context, "table_id")
        identity = self._read_identity()
        connector = self._read_connector(actor)
        if not table_id:
            data = connector.run_json(
                [
                    "base",
                    "+table-list",
                    "--base-token",
                    token,
                    "--format",
                    "json",
                    "--as",
                    identity,
                ]
            )
            enriched = _badcase_context_needs_locator(
                context=context,
                next_action="已读取 Base 表清单；请补充 table 参数或具体记录链接后再映射字段。",
            )
            tables = _lark_base_tables(data)
            if tables:
                enriched["available_tables"] = tables[:10]
            return enriched
        args = [
            "base",
            "+record-list",
            "--base-token",
            token,
            "--table-id",
            table_id,
            "--limit",
            "20",
            "--format",
            "json",
            "--as",
            identity,
        ]
        view_id = _object_string(context, "view_id")
        if view_id:
            args.extend(["--view-id", view_id])
        data = connector.run_json(args)
        record_result = _badcase_fields_from_base_records(
            _lark_base_records(data),
            preferred_record_id=_object_string(context, "record_id"),
        )
        enriched = _badcase_context_with_content(
            context=context,
            fields=_object_fields(record_result, "fields"),
            preview=_object_string(record_result, "preview"),
            next_action="已读取 Base 记录并尝试按字段名映射 badcase 字段。",
        )
        selected_record = _object_string(record_result, "selected_record")
        if selected_record:
            enriched["selected_record"] = selected_record
        record_count = record_result.get("record_count")
        if isinstance(record_count, int):
            enriched["record_count"] = record_count
        return enriched

    def debug_case_from_sheet_rows(
        self,
        data: dict[str, object],
        *,
        preferred_row_id: str,
        preferred_row_label: str = "",
    ) -> dict[str, object]:
        rows = _lark_rows_json_entries(data)
        if not rows:
            return {"fields": {}, "row_count": 0, "preview": "", "status": "no_rows"}
        header_index = _first_non_empty_lark_row_index(rows)
        if header_index is None:
            return {"fields": {}, "row_count": 0, "preview": "", "status": "no_header"}
        headers = {
            column: _stringify_lark_cell(value) for column, value in rows[header_index][1].items()
        }
        data_rows = rows[header_index + 1 :]
        fallback_preview = ""
        first_unmapped_result: dict[str, object] | None = None
        schema_agent = self._schema_mapping_agent()
        sample_rows = self.schema_mapping_sample_rows(headers=headers, data_rows=data_rows)
        for row_number, values in data_rows:
            if preferred_row_id and str(row_number) != preferred_row_id:
                continue
            named_values = {
                header: _stringify_lark_cell(values.get(column, ""))
                for column, header in headers.items()
                if header
            }
            if not fallback_preview:
                fallback_preview = _named_values_preview(named_values)
            if preferred_row_label and not _sheet_row_matches_target_label(
                named_values=named_values,
                values=values,
                target_label=preferred_row_label,
            ):
                continue
            schema_result = self.run_case_intake_schema_mapping_agent(
                schema_agent=schema_agent,
                headers=headers,
                values=values,
                sheet_row_id=str(row_number),
                target_label=preferred_row_label,
                sample_rows=sample_rows,
            )
            if schema_result.case is not None:
                case = schema_result.case
                return {
                    "fields": _badcase_fields_from_debug_case(case),
                    "field_columns": self.debug_case_field_columns_from_schema_result(
                        schema_result
                    ),
                    "schema_mappings": self.schema_mapping_payload(schema_result),
                    "schema_warnings": schema_result.warnings,
                    "schema_agent": self.schema_agent_payload(schema_result),
                    "normalized_row": schema_result.normalized_row,
                    "debug_case": case.model_dump(mode="json"),
                    "selected_row": str(row_number),
                    "selected_label": preferred_row_label,
                    "row_count": len(data_rows),
                    "preview": _named_values_preview(named_values),
                    "status": "imported",
                    "import_protocol": "case_intake_schema_agent+parse_spreadsheet_rows",
                }
            unmapped_result = self.sheet_row_schema_mapping_failure_result(
                schema_result=schema_result,
                row_number=row_number,
                named_values=named_values,
                row_count=len(data_rows),
                preferred_row_label=preferred_row_label,
            )
            if preferred_row_id or preferred_row_label:
                return unmapped_result
            if first_unmapped_result is None:
                first_unmapped_result = unmapped_result
        if first_unmapped_result is not None:
            return first_unmapped_result
        return {
            "fields": {},
            "row_count": len(data_rows),
            "preview": fallback_preview,
            "status": "not_found"
            if preferred_row_id or preferred_row_label
            else "no_importable_rows",
            "selected_label": preferred_row_label,
        }

    def sheet_row_schema_mapping_failure_result(
        self,
        *,
        schema_result: SpreadsheetSchemaMappingResult,
        row_number: int,
        named_values: dict[str, str],
        row_count: int,
        preferred_row_label: str,
    ) -> dict[str, object]:
        error_message = ""
        if schema_result.rejected_row is not None:
            error_message = schema_result.rejected_row.error_message
        return {
            "fields": {},
            "selected_row": str(row_number),
            "selected_label": preferred_row_label,
            "row_count": row_count,
            "preview": _named_values_preview(named_values),
            "status": "rejected",
            "error_message": error_message,
            "missing_spreadsheet_fields": schema_result.missing_fields,
            "schema_mappings": self.schema_mapping_payload(schema_result),
            "schema_warnings": schema_result.warnings,
            "schema_agent": self.schema_agent_payload(schema_result),
            "normalized_row": schema_result.normalized_row,
            "import_protocol": "case_intake_schema_agent+parse_spreadsheet_rows",
        }

    def run_case_intake_schema_mapping_agent(
        self,
        *,
        schema_agent: SpreadsheetSchemaMappingAgent,
        headers: dict[str, str],
        values: dict[str, object],
        sheet_row_id: str,
        target_label: str,
        sample_rows: list[dict[str, object]],
    ) -> SpreadsheetSchemaMappingResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                schema_agent.map_row_with_model(
                    headers=headers,
                    values=values,
                    sheet_row_id=sheet_row_id,
                    target_label=target_label,
                    sample_rows=sample_rows,
                )
            )
        return schema_agent.map_row(
            headers=headers,
            values=values,
            sheet_row_id=sheet_row_id,
            target_label=target_label,
            sample_rows=sample_rows,
        )

    def schema_mapping_sample_rows(
        self,
        *,
        headers: dict[str, str],
        data_rows: list[tuple[int, dict[str, object]]],
    ) -> list[dict[str, object]]:
        samples: list[dict[str, object]] = []
        for _, values in data_rows[:5]:
            samples.append(
                {
                    header: _stringify_lark_cell(values.get(column, ""))
                    for column, header in headers.items()
                    if header
                }
            )
        return samples

    def debug_case_field_columns_from_schema_result(
        self,
        schema_result: SpreadsheetSchemaMappingResult,
    ) -> dict[str, str]:
        columns: dict[str, str] = {}
        image_mapping = schema_result.mappings.get("image_uri")
        if image_mapping is not None:
            columns["input_source"] = image_mapping.source_column
        return columns

    def schema_mapping_payload(
        self,
        schema_result: SpreadsheetSchemaMappingResult,
    ) -> dict[str, dict[str, object]]:
        return {
            field: mapping.model_dump(mode="json", exclude={"source_value"})
            for field, mapping in schema_result.mappings.items()
        }

    def schema_agent_payload(
        self, schema_result: SpreadsheetSchemaMappingResult
    ) -> dict[str, object]:
        return {
            "agent_mode": schema_result.agent_mode,
            "model_provider": schema_result.model_provider,
            "model_id": schema_result.model_id,
            "model_name": schema_result.model_name,
            "model_error": schema_result.model_error,
        }

    def sheet_row_context_with_import_result(
        self,
        *,
        context: dict[str, object],
        row_result: dict[str, object],
        fields: dict[str, str],
    ) -> dict[str, object]:
        debug_case = _debug_case_from_row_result(row_result)
        if debug_case is not None:
            enriched = _badcase_context_with_content(
                context=context,
                fields=fields,
                preview=_object_string(row_result, "preview"),
                next_action="已按 Debug Agent 表格导入协议读取表头并解析该行。",
            )
            enriched["debug_case"] = debug_case.model_dump(mode="json")
            enriched["debug_case_id"] = debug_case.case_id
            enriched["import_protocol"] = (
                _object_string(row_result, "import_protocol") or "parse_spreadsheet_rows"
            )
            schema_mappings = row_result.get("schema_mappings")
            if isinstance(schema_mappings, dict):
                enriched["schema_mappings"] = schema_mappings
            schema_warnings = row_result.get("schema_warnings")
            if isinstance(schema_warnings, list):
                enriched["schema_warnings"] = [str(item) for item in schema_warnings]
            schema_agent = row_result.get("schema_agent")
            if isinstance(schema_agent, dict):
                enriched["schema_agent"] = schema_agent
            return enriched
        enriched = dict(context)
        status = _object_string(row_result, "status") or "content_read"
        enriched["status"] = "spreadsheet_row_rejected" if status == "rejected" else status
        preview = _object_string(row_result, "preview")
        if preview:
            enriched["content_preview"] = _clip_text(preview, 800)
        error_message = _object_string(row_result, "error_message")
        if error_message:
            enriched["error_message"] = _clip_text(error_message, 500)
        missing_fields = row_result.get("missing_spreadsheet_fields")
        if isinstance(missing_fields, list):
            enriched["missing_spreadsheet_fields"] = [
                str(item) for item in missing_fields if str(item).strip()
            ]
        enriched["import_protocol"] = (
            _object_string(row_result, "import_protocol") or "parse_spreadsheet_rows"
        )
        schema_mappings = row_result.get("schema_mappings")
        if isinstance(schema_mappings, dict):
            enriched["schema_mappings"] = schema_mappings
        schema_warnings = row_result.get("schema_warnings")
        if isinstance(schema_warnings, list):
            enriched["schema_warnings"] = [str(item) for item in schema_warnings]
        schema_agent = row_result.get("schema_agent")
        if isinstance(schema_agent, dict):
            enriched["schema_agent"] = schema_agent
        enriched["next_action"] = _sheet_row_import_next_action(row_result)
        return enriched

    def resolve_lark_sheet_media_input(
        self,
        *,
        connector: LarkCliConnector,
        token: str,
        sheet_id: str,
        row_result: dict[str, object],
        fields: dict[str, str],
    ) -> dict[str, object]:
        input_source = fields.get("input_source", "").strip()
        if not _input_source_requires_media_resolution(input_source):
            return {}
        field_columns = row_result.get("field_columns")
        source_column = ""
        if isinstance(field_columns, dict):
            value = field_columns.get("input_source")
            source_column = value if isinstance(value, str) else ""
        selected_row = _object_string(row_result, "selected_row")
        if not source_column or not selected_row:
            fields.pop("input_source", None)
            return {
                "status": "missing_attachment",
                "display_name": input_source,
                "next_action": "表格里只有媒体文件名，没有可下载附件信息；请补充可访问的视频链接或上传附件。",
            }
        cell = self.lark_sheet_cell(
            connector=connector,
            spreadsheet_token=token,
            sheet_id=sheet_id,
            column=source_column,
            row=selected_row,
        )
        attachment = _lark_sheet_cell_attachment(cell)
        if not attachment:
            fields.pop("input_source", None)
            return {
                "status": "missing_attachment",
                "display_name": input_source,
                "cell": f"{source_column}{selected_row}",
                "next_action": "表格媒体单元格未返回附件 token；请补充可访问的视频链接或重新上传附件。",
            }
        try:
            downloaded = self.download_lark_sheet_attachment(
                connector=connector,
                attachment=attachment,
                fallback_name=input_source,
            )
        except LarkCliError as exc:
            fields.pop("input_source", None)
            return _lark_sheet_attachment_download_failed(
                attachment=attachment,
                cell=f"{source_column}{selected_row}",
                exc=exc,
            )
        fields["input_source"] = _object_string(downloaded, "uri")
        return {
            **attachment,
            **downloaded,
            "status": "downloaded",
            "cell": f"{source_column}{selected_row}",
            "next_action": "已下载表格视频附件，并作为 Debug 任务媒体输入。",
        }

    def lark_sheet_cell(
        self,
        *,
        connector: LarkCliConnector,
        spreadsheet_token: str,
        sheet_id: str,
        column: str,
        row: str,
    ) -> dict[str, object]:
        data = connector.run_json(
            [
                "sheets",
                "+cells-get",
                "--spreadsheet-token",
                spreadsheet_token,
                "--sheet-id",
                sheet_id,
                "--range",
                f"{column}{row}:{column}{row}",
                "--include",
                "value,formula,comment",
                "--format",
                "json",
                "--as",
                self._read_identity(),
            ]
        )
        ranges = data.get("ranges")
        if not isinstance(ranges, list) or not ranges:
            return {}
        first_range = ranges[0]
        if not isinstance(first_range, dict):
            return {}
        cells = first_range.get("cells")
        if not isinstance(cells, list) or not cells:
            return {}
        first_row = cells[0]
        if not isinstance(first_row, list) or not first_row:
            return {}
        first_cell = first_row[0]
        return first_cell if isinstance(first_cell, dict) else {}

    def download_lark_sheet_attachment(
        self,
        *,
        connector: LarkCliConnector,
        attachment: dict[str, object],
        fallback_name: str,
    ) -> dict[str, object]:
        token = _object_string(attachment, "attachment_token")
        if not token:
            raise LarkCliError(
                "Sheet attachment token is missing.", error_type="invalid_attachment"
            )
        output_path = self.lark_sheet_attachment_output_path(
            attachment=attachment, fallback_name=fallback_name
        )
        output_arg = self.cwd_relative_path(output_path)
        if output_path.exists():
            output_path.unlink()
        connector.run_json(
            [
                "api",
                "GET",
                f"/open-apis/drive/v1/medias/{token}/download",
                "--output",
                output_arg,
                "--format",
                "json",
                "--as",
                self._read_identity(),
            ]
        )
        return {
            "local_path": str(output_path),
            "uri": output_path.resolve().as_uri(),
        }

    def cwd_relative_path(self, path: Path) -> str:
        resolved_path = path.resolve()
        cwd = Path.cwd().resolve()
        try:
            return resolved_path.relative_to(cwd).as_posix()
        except ValueError:
            return str(resolved_path)

    def lark_sheet_attachment_output_path(
        self,
        *,
        attachment: dict[str, object],
        fallback_name: str,
    ) -> Path:
        media_dir = self._media_dir()
        media_dir.mkdir(parents=True, exist_ok=True)
        token = _object_string(attachment, "attachment_token") or str(uuid4())
        display_name = _object_string(attachment, "name") or fallback_name or token
        display_path = Path(display_name)
        suffix = display_path.suffix or self.suffix_for_mime_type(
            _object_string(attachment, "mime_type")
        )
        stem = safe_path_fragment(display_path.stem or "attachment")
        return media_dir / f"{safe_path_fragment(token)[:16]}-{stem}{suffix}"

    def suffix_for_mime_type(self, mime_type: str) -> str:
        mapping = {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
        }
        return mapping.get(mime_type.lower(), "")

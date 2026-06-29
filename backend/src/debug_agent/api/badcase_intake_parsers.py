from __future__ import annotations

import json
import re
from urllib.parse import unquote, urlparse

from pydantic import ValidationError

from debug_agent.cases.models import DebugCase
from debug_agent.spreadsheets.lark import LarkCliError


def _extract_badcase_fields_from_text(text: str) -> dict[str, str]:
    normalized = text.strip()
    labeled_model_output = _extract_labeled_value(
        normalized,
        (
            "模型输出",
            "实际输出",
            "识别结果",
            "输出",
            "predict",
            "model_output",
            "actual_output",
            "prediction",
            "observed",
            "output",
        ),
    )
    labeled_issue_summary = _extract_labeled_value(
        normalized,
        (
            "错误现象",
            "问题现象",
            "问题",
            "现象",
            "错在",
            "gpt_response",
            "issue_summary",
            "issue",
            "problem",
            "failure",
            "bug",
        ),
    )
    return {
        "input_source": _extract_labeled_value(
            normalized,
            (
                "原始输入",
                "video",
                "视频",
                "file",
                "文件",
                "输入",
                "图片",
                "链接",
                "样本",
                "input_source",
                "input",
                "image_uri",
                "video_uri",
                "source",
                "prompt",
            ),
        ),
        "model_output": labeled_model_output or _extract_natural_model_output(normalized),
        "expected_output": _extract_labeled_value(
            normalized,
            (
                "期望结果",
                "期望输出",
                "正确答案",
                "正确应该是",
                "正确是",
                "expected_output",
                "expected",
                "reference",
                "reference_answer",
                "golden",
                "answer",
            ),
        ),
        "issue_summary": labeled_issue_summary or _extract_natural_issue_summary(normalized),
        "task_type": _extract_labeled_value(
            normalized, ("任务类型", "任务", "task_type", "task type")
        ),
        "scoring_standard": _extract_labeled_value(
            normalized, ("评测标准", "评分标准", "判断标准", "scoring_standard", "scoring")
        ),
    }


def _extract_natural_model_output(text: str) -> str:
    for pattern in (
        r"模型(?:把|将).{0,40}?识别成(?:了)?\s*([^\s，。；;,]+)",
        r"识别成(?:了)?\s*([^\s，。；;,]+)",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" \n\r\t。；;，,")
    return ""


def _extract_natural_issue_summary(text: str) -> str:
    text_without_links = re.sub(r"https?://[^\s，。；；,]+", " ", text)
    for pattern in (
        r"(模型(?:把|将).{0,40}?识别成(?:了)?\s*[^\s，。；;,]+)",
        r"([^。；;\n]{0,40}识别错了[^。；;\n]{0,80})",
        r"([^。；;\n]{0,40}识别成了?[^。；;\n]{0,80})",
    ):
        match = re.search(pattern, text_without_links, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" \n\r\t。；;，,")
    return ""


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        separator = r"\s*[：:=]\s*" if _is_ascii_label(label) else r"\s*[：:=是]?\s*"
        pattern = rf"{re.escape(label)}{separator}(.+?)(?=(?:\n|[；;，,])\s*(?:原始输入|video|视频|file|文件|输入|图片|链接|样本|input_source|input|image_uri|video_uri|source|prompt|模型输出|实际输出|识别结果|输出|predict|model_output|actual_output|prediction|observed|output|期望结果|期望输出|正确答案|正确应该是|正确是|expected_output|expected|reference|reference_answer|golden|answer|错误现象|问题现象|问题|现象|错在|gpt_response|issue_summary|issue|problem|failure|bug|任务类型|任务|task_type|task type|评测标准|评分标准|判断标准|scoring_standard|scoring)\s*[：:=是]?|$)"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip(" \n\r\t。；;，,")
    return ""


def _is_ascii_label(label: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_ ]+", label))


def _extract_links(text: str) -> list[str]:
    return re.findall(r"https?://[^\s，。；；,]+", text)


def _badcase_sheet_target_label(text: str) -> str:
    text_without_links = re.sub(r"https?://[^\s，。；；,]+", " ", text)
    for pattern in (r"\b[A-Z][A-Z0-9]{1,10}[-_]\d{1,8}\b",):
        match = re.search(pattern, text_without_links)
        if match:
            return match.group(0).strip()
    return ""


BADCASE_DRAFT_FIELD_KEYS = (
    "input_source",
    "model_output",
    "expected_output",
    "issue_summary",
    "task_type",
    "scoring_standard",
)

BADCASE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "input_source": (
        "原始输入",
        "video",
        "视频",
        "文件",
        "file",
        "video_uri",
        "video_url",
        "输入",
        "图片",
        "链接",
        "样本",
        "input_source",
        "input",
        "image_uri",
        "source",
        "user prompt",
        "prompt",
    ),
    "model_output": (
        "模型输出",
        "实际输出",
        "识别结果",
        "输出",
        "predict",
        "model_output",
        "actual_output",
        "prediction",
        "model prediction",
        "observed",
        "output",
    ),
    "expected_output": (
        "期望结果",
        "期望输出",
        "参考答案",
        "正确答案",
        "正确应该是",
        "正确是",
        "expected_output",
        "expected",
        "reference",
        "reference_answer",
        "golden",
        "answer",
    ),
    "issue_summary": (
        "错误现象",
        "问题现象",
        "问题",
        "现象",
        "错在",
        "gpt_response",
        "评估问题反馈",
        "错误原因",
        "要点备注",
        "evaluate result",
        "issue_summary",
        "issue",
        "problem",
        "failure",
        "bug",
    ),
    "task_type": ("任务类型", "任务", "task_type", "task type"),
    "scoring_standard": (
        "评测标准",
        "评分标准",
        "判断标准",
        "评分标准（详细版）",
        "评分标准（宽松版）",
        "scoring_standard",
        "scoring",
        "rubric",
    ),
}


def _badcase_fields_from_link_contexts(contexts: list[dict[str, object]]) -> dict[str, str]:
    merged = {key: "" for key in BADCASE_DRAFT_FIELD_KEYS}
    for context in contexts:
        fields = context.get("badcase_fields")
        if not isinstance(fields, dict):
            continue
        for key in BADCASE_DRAFT_FIELD_KEYS:
            if merged[key]:
                continue
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
    return merged


def _debug_case_from_link_contexts(contexts: list[dict[str, object]]) -> DebugCase | None:
    for context in contexts:
        debug_case = _debug_case_from_row_result(context)
        if debug_case is not None:
            return debug_case
    return None


def _missing_spreadsheet_fields_from_link_contexts(contexts: list[dict[str, object]]) -> list[str]:
    for context in contexts:
        value = context.get("missing_spreadsheet_fields")
        if isinstance(value, list):
            fields = [str(item) for item in value if str(item).strip()]
            if fields:
                return fields
    return []


def _badcase_input_source_from_links(contexts: list[dict[str, object]]) -> str:
    for context in contexts:
        if _object_string(context, "link_type") == "external_url":
            return _object_string(context, "url")
    return ""


def _badcase_context_needs_locator(
    *,
    context: dict[str, object],
    next_action: str,
) -> dict[str, object]:
    enriched = dict(context)
    enriched["status"] = "needs_locator"
    enriched["next_action"] = next_action
    return enriched


def _badcase_context_read_failed(
    *,
    context: dict[str, object],
    exc: LarkCliError,
) -> dict[str, object]:
    enriched = dict(context)
    enriched["status"] = "read_failed"
    enriched["error_type"] = exc.error_type
    enriched["error_message"] = _clip_text(str(exc), 500)
    if exc.hint:
        enriched["hint"] = exc.hint
    if exc.permission_scopes:
        enriched["permission_scopes"] = exc.permission_scopes
    enriched["next_action"] = "读取飞书资源失败；请检查机器人权限、资源访问权限或链接定位参数。"
    return enriched


def _badcase_context_with_content(
    *,
    context: dict[str, object],
    fields: dict[str, str],
    preview: str,
    next_action: str,
) -> dict[str, object]:
    normalized_fields = {
        key: value.strip()
        for key, value in fields.items()
        if key in BADCASE_DRAFT_FIELD_KEYS and value.strip()
    }
    enriched = dict(context)
    enriched["status"] = "content_resolved" if normalized_fields else "content_read"
    if normalized_fields:
        enriched["badcase_fields"] = normalized_fields
    if preview.strip():
        enriched["content_preview"] = _clip_text(preview.strip(), 800)
    enriched["next_action"] = (
        next_action
        if normalized_fields
        else "已读取资源内容，但未识别到标准 badcase 字段，请继续补充模型输出、期望结果和错误现象。"
    )
    return enriched


def _sheet_row_import_next_action(row_result: dict[str, object]) -> str:
    status = _object_string(row_result, "status")
    if status == "rejected":
        error_message = _object_string(row_result, "error_message")
        return f"表格行未通过 Debug Agent 既有导入协议，补齐表头/字段后我再提交： {error_message}"
    if status == "not_found":
        selected_label = _object_string(row_result, "selected_label")
        if selected_label:
            return f"没有找到包含 `{selected_label}` 的可导入表格行，请补充行号或检查样本 ID。"
        return "没有找到指定表格行，请补充 row 参数或样本 ID。"
    if status in {"no_rows", "no_header"}:
        return "表格没有可读取的表头或数据行，请先补齐表头和样本行。"
    return "已读取表格，但 Case Intake Agent 未能整理出合法 DebugCase；请检查表格是否包含样本 ID、用户输入、模型输出、参考答案和评分规则。"


def _debug_case_from_row_result(row_result: dict[str, object]) -> DebugCase | None:
    payload = row_result.get("debug_case")
    if not isinstance(payload, dict):
        return None
    try:
        return DebugCase.model_validate(payload)
    except ValidationError:
        return None


def _badcase_fields_from_debug_case(case: DebugCase) -> dict[str, str]:
    fields = {key: "" for key in BADCASE_DRAFT_FIELD_KEYS}
    fields["input_source"] = case.image_uri
    fields["task_type"] = case.task_type
    fields["scoring_standard"] = case.scoring_standard
    if case.predictions:
        fields["model_output"] = case.predictions[0].raw_output
    if case.expected_output:
        fields["expected_output"] = json.dumps(case.expected_output, ensure_ascii=False)
    if case.human_notes.root_cause:
        fields["issue_summary"] = case.human_notes.root_cause
    return fields


def _sheet_row_matches_target_label(
    *,
    named_values: dict[str, str],
    values: dict[str, object],
    target_label: str,
) -> bool:
    target = _normalized_sheet_target_label(target_label)
    if not target:
        return False
    cell_values = [
        *named_values.values(),
        *[_stringify_lark_cell(value) for value in values.values()],
    ]
    return any(target in _normalized_sheet_target_label(value) for value in cell_values)


def _normalized_sheet_target_label(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _input_source_requires_media_resolution(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    parsed = urlparse(stripped)
    if parsed.scheme in {"http", "https", "data", "tos", "file"}:
        return False
    return (
        stripped.lower()
        .split("?", 1)[0]
        .endswith(
            (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".png", ".jpg", ".jpeg", ".webp")
        )
    )


def _lark_sheet_cell_attachment(cell: dict[str, object]) -> dict[str, object]:
    rich_text = cell.get("rich_text")
    if not isinstance(rich_text, list):
        return {}
    for item in rich_text:
        if not isinstance(item, dict) or item.get("type") != "attachment":
            continue
        token = item.get("attachment_token")
        if not isinstance(token, str) or not token.strip():
            continue
        attachment: dict[str, object] = {
            "attachment_token": token.strip(),
            "name": _object_string(item, "text") or _object_string(item, "name"),
            "mime_type": _object_string(item, "mime_type"),
        }
        file_size = item.get("file_size")
        if isinstance(file_size, int):
            attachment["file_size"] = file_size
        return attachment
    return {}


def _lark_sheet_attachment_download_failed(
    *,
    attachment: dict[str, object],
    cell: str,
    exc: LarkCliError,
) -> dict[str, object]:
    result = {
        **attachment,
        "status": "download_failed",
        "cell": cell,
        "error_type": exc.error_type,
        "error_message": _clip_text(str(exc), 500),
        "next_action": "已识别到表格视频附件，但机器人没有文档媒体下载权限或下载失败；请开通 docs:document.media:download 后重试。",
    }
    permission_scopes = (
        _preferred_lark_sheet_media_permission_scopes(exc.permission_scopes)
        or _permission_scopes_from_text(str(exc))
        or ["docs:document.media:download"]
    )
    if permission_scopes:
        result["permission_scopes"] = permission_scopes
    if exc.hint:
        result["hint"] = exc.hint
    return result


def _preferred_lark_sheet_media_permission_scopes(scopes: list[str]) -> list[str]:
    if "docs:document.media:download" in scopes:
        return ["docs:document.media:download"]
    return scopes


def _permission_scopes_from_text(text: str) -> list[str]:
    scopes: list[str] = []
    for scope in re.findall(r"\b[a-z]+:[a-zA-Z0-9_.:-]+", text):
        if scope not in scopes:
            scopes.append(scope)
    return scopes


def _badcase_fields_from_base_records(
    records: list[dict[str, object]],
    *,
    preferred_record_id: str,
) -> dict[str, object]:
    fallback_preview = ""
    for record in records:
        record_id = _object_string(record, "record_id") or _object_string(record, "id")
        if preferred_record_id and record_id != preferred_record_id:
            continue
        named_values = _base_record_named_values(record)
        if not fallback_preview:
            fallback_preview = _named_values_preview(named_values)
        fields = _badcase_fields_from_named_values(named_values)
        if any(fields.values()):
            return {
                "fields": fields,
                "selected_record": record_id,
                "record_count": len(records),
                "preview": _named_values_preview(named_values),
            }
    return {"fields": {}, "record_count": len(records), "preview": fallback_preview}


def _badcase_fields_from_named_values(values: dict[str, str]) -> dict[str, str]:
    fields = {key: "" for key in BADCASE_DRAFT_FIELD_KEYS}
    normalized_values = {
        _normalized_badcase_field_name(name): value.strip()
        for name, value in values.items()
        if value.strip()
    }
    for key, aliases in BADCASE_FIELD_ALIASES.items():
        for alias in aliases:
            value = _badcase_named_value_for_alias(normalized_values, alias)
            if value:
                fields[key] = value
                break
    return fields


def _badcase_named_value_for_alias(
    normalized_values: dict[str, str],
    alias: str,
) -> str:
    alias_key = _normalized_badcase_field_name(alias)
    exact = normalized_values.get(alias_key, "")
    if exact:
        return exact
    if len(alias_key) < 4:
        return ""
    for field_name, value in normalized_values.items():
        if field_name.startswith(alias_key) or alias_key in field_name:
            return value
    return ""


def _lark_rows_json_entries(data: dict[str, object]) -> list[tuple[int, dict[str, object]]]:
    rows_raw = data.get("rows", [])
    if not isinstance(rows_raw, list):
        return []
    rows: list[tuple[int, dict[str, object]]] = []
    for row_raw in rows_raw:
        if not isinstance(row_raw, dict):
            continue
        row_number = row_raw.get("row_number")
        values_raw = row_raw.get("values", {})
        if isinstance(row_number, int) and isinstance(values_raw, dict):
            rows.append((row_number, {str(key): value for key, value in values_raw.items()}))
    return sorted(rows)


def _first_non_empty_lark_row_index(rows: list[tuple[int, dict[str, object]]]) -> int | None:
    for index, (_, values) in enumerate(rows):
        if any(_stringify_lark_cell(value).strip() for value in values.values()):
            return index
    return None


def _lark_base_records(data: dict[str, object]) -> list[dict[str, object]]:
    for key in ("records", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    nested = data.get("data")
    if isinstance(nested, dict):
        return _lark_base_records(nested)
    return []


def _lark_base_tables(data: dict[str, object]) -> list[dict[str, str]]:
    tables_raw = data.get("tables") or data.get("items")
    if not isinstance(tables_raw, list):
        return []
    tables: list[dict[str, str]] = []
    for table in tables_raw:
        if not isinstance(table, dict):
            continue
        table_id = _object_string(table, "table_id") or _object_string(table, "id")
        name = _object_string(table, "name") or _object_string(table, "title")
        if table_id or name:
            tables.append({"table_id": table_id, "name": name})
    return tables


def _base_record_named_values(record: dict[str, object]) -> dict[str, str]:
    fields = record.get("fields")
    if isinstance(fields, dict):
        return {str(key): _stringify_lark_cell(value) for key, value in fields.items()}
    return {
        str(key): _stringify_lark_cell(value)
        for key, value in record.items()
        if key not in {"record_id", "id", "created_by", "created_time", "last_modified_time"}
    }


def _object_fields(payload: dict[str, object], key: str) -> dict[str, str]:
    value = payload.get(key)
    if not isinstance(value, dict):
        return {}
    return {
        str(field_key): field_value.strip()
        for field_key, field_value in value.items()
        if isinstance(field_value, str) and field_value.strip()
    }


def _lark_data_text(value: object, *, depth: int = 0) -> str:
    if depth > 8:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(_lark_data_text(item, depth=depth + 1) for item in value)
    if isinstance(value, dict):
        priority_keys = (
            "markdown",
            "content",
            "text",
            "plain_text",
            "xml",
            "title",
            "excerpt",
            "fragments",
            "blocks",
            "children",
        )
        texts: list[str] = []
        for key in priority_keys:
            if key in value:
                texts.append(_lark_data_text(value[key], depth=depth + 1))
        for key, item in value.items():
            if key not in priority_keys:
                texts.append(_lark_data_text(item, depth=depth + 1))
        return "\n".join(text for text in texts if text.strip())
    return ""


def _stringify_lark_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(item for item in (_stringify_lark_cell(item) for item in value) if item)
    if isinstance(value, dict):
        for key in ("text", "value", "name", "url", "href", "link"):
            cell_value = value.get(key)
            text = _stringify_lark_cell(cell_value)
            if text:
                return text
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _normalized_badcase_field_name(value: str) -> str:
    return re.sub(r"[\s_\-：:=]+", "", value.strip().lower())


def _named_values_preview(values: dict[str, str]) -> str:
    lines = [f"{name}: {value}" for name, value in values.items() if value.strip()]
    return "\n".join(lines[:12])


def _clip_text(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else f"{value[:max_length]}..."


def _badcase_link_context(link: str) -> dict[str, object] | None:
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")
    parts = [unquote(part) for part in path.split("/") if part]
    if not parts:
        return None
    if _is_debug_agent_host(host):
        return _debug_agent_link_context(link=link, parts=parts)
    if not _is_lark_resource_host(host):
        return {
            "type": "link_context",
            "link_type": "external_url",
            "resource": "外部链接",
            "url": link,
            "status": "recognized",
            "next_action": "作为 badcase 原始输入保存；如需读取内容，需要补充具体连接器。",
        }
    link_type, resource = _lark_link_type_and_resource(parts)
    token = parts[1] if len(parts) > 1 else ""
    context: dict[str, object] = {
        "type": "link_context",
        "link_type": link_type,
        "resource": resource,
        "url": link,
        "token": token,
        "status": "metadata_only",
        "next_action": _lark_link_next_action(link_type),
    }
    sheet_id = _query_value(parsed.query, "sheet")
    if sheet_id:
        context["sheet_id"] = sheet_id
    row_id = _query_value(parsed.query, "row") or _query_value(parsed.query, "row_id")
    if row_id:
        context["row_id"] = row_id
    table_id = _query_value(parsed.query, "table")
    if table_id:
        context["table_id"] = table_id
    record_id = _query_value(parsed.query, "record") or _query_value(parsed.query, "record_id")
    if record_id:
        context["record_id"] = record_id
    view_id = _query_value(parsed.query, "view")
    if view_id:
        context["view_id"] = view_id
    return context


def _is_debug_agent_host(host: str) -> bool:
    return host.startswith("localhost") or host.startswith("127.0.0.1") or "debug-agent" in host


def _is_lark_resource_host(host: str) -> bool:
    return any(
        domain in host for domain in ("larksuite.com", "larkoffice.com", "feishu.cn", "doubao.com")
    )


def _debug_agent_link_context(*, link: str, parts: list[str]) -> dict[str, object]:
    link_type = "debug_agent_link"
    resource = "Debug Agent 链接"
    identifier = ""
    if len(parts) >= 2 and parts[0] == "jobs":
        identifier = parts[1]
        link_type = (
            "debug_agent_report" if len(parts) >= 3 and parts[2] == "report" else "debug_agent_job"
        )
        resource = "Debug Agent 报告" if link_type == "debug_agent_report" else "Debug Agent 任务"
    elif len(parts) >= 2 and parts[0] == "debug-batches":
        identifier = parts[1]
        link_type = "debug_agent_batch"
        resource = "Debug Agent 批次"
    return {
        "type": "link_context",
        "link_type": link_type,
        "resource": resource,
        "url": link,
        "identifier": identifier,
        "status": "recognized",
        "next_action": "可用于查询任务、报告或批次状态。",
    }


def _lark_link_type_and_resource(parts: list[str]) -> tuple[str, str]:
    head = parts[0].lower()
    if head in {"docx", "docs"}:
        return "lark_doc", "飞书文档"
    if head == "wiki":
        return "lark_wiki", "飞书知识库"
    if head in {"sheets", "sheet"}:
        return "lark_sheet", "飞书电子表格"
    if head in {"base", "bitable"}:
        return "lark_base", "飞书多维表格"
    if head in {"file", "folder", "drive"}:
        return "lark_drive", "飞书云盘资源"
    if head == "minutes":
        return "lark_minutes", "飞书妙记"
    if head == "slides":
        return "lark_slides", "飞书幻灯片"
    return "lark_link", "飞书链接"


def _lark_link_next_action(link_type: str) -> str:
    actions = {
        "lark_doc": "下一步接入文档读取后，可从正文提取 badcase 信息。",
        "lark_wiki": "下一步接入知识库读取后，可从节点文档提取 badcase 信息。",
        "lark_sheet": "下一步接入表格读取后，可选择样本行并映射字段。",
        "lark_base": "下一步接入 Base 读取后，可选择记录并映射字段。",
        "lark_drive": "下一步接入云盘下载后，可作为图片、视频或文件输入。",
        "lark_minutes": "下一步接入妙记读取后，可提取会议中的问题描述。",
        "lark_slides": "下一步接入幻灯片读取后，可提取页面中的样本说明。",
    }
    return actions.get(link_type, "已识别为飞书资源；下一步需要接入对应读取器。")


def _query_value(query: str, key: str) -> str:
    for item in query.split("&"):
        if "=" not in item:
            continue
        item_key, value = item.split("=", 1)
        if item_key == key:
            return unquote(value)
    return ""


def _missing_badcase_draft_fields(
    *,
    input_source: str,
    model_output: str,
    expected_output: str,
    issue_summary: str,
) -> list[str]:
    missing: list[str] = []
    if not input_source.strip():
        missing.append("input_source")
    if not model_output.strip():
        missing.append("model_output")
    if not expected_output.strip():
        missing.append("expected_output")
    if not issue_summary.strip():
        missing.append("issue_summary")
    return missing


def _normalized_badcase_task_type(value: str) -> str:
    normalized = value.strip()
    if normalized in {
        "classification",
        "handwriting_ocr",
        "image_detection",
        "video_detection",
        "multimodal_detection",
        "generic_json",
        "generic_video_json",
    }:
        return normalized
    return "generic_json"


def _json_object_or_text(value: str) -> object:
    stripped = value.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"answer": stripped}


def _badcase_attachment_source(attachments: list[dict[str, object]]) -> str:
    for attachment in attachments:
        if _object_string(attachment, "type") == "link_context":
            continue
        kind = (
            _object_string(attachment, "type") or _object_string(attachment, "tag") or "attachment"
        )
        identifier = (
            _object_string(attachment, "file_key")
            or _object_string(attachment, "image_key")
            or _object_string(attachment, "key")
            or _object_string(attachment, "href")
            or _object_string(attachment, "url")
        )
        name = _object_string(attachment, "name") or _object_string(attachment, "file_name")
        if identifier and name:
            return f"attachment:{kind}:{identifier} ({name})"
        if identifier:
            return f"attachment:{kind}:{identifier}"
        if name:
            return f"attachment:{kind}:{name}"
    return ""


def _dedupe_badcase_attachments(
    attachments: list[dict[str, object]],
) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    positions: dict[str, int] = {}
    for attachment in attachments:
        marker = _badcase_attachment_marker(attachment)
        if marker in positions:
            deduped[positions[marker]] = attachment
            continue
        positions[marker] = len(deduped)
        deduped.append(attachment)
    return deduped


def _badcase_attachment_marker(attachment: dict[str, object]) -> str:
    if _object_string(attachment, "type") == "link_context":
        url = _object_string(attachment, "url")
        token = _object_string(attachment, "token")
        link_type = _object_string(attachment, "link_type")
        if url or token:
            return f"link_context:{link_type}:{url or token}"
    return json.dumps(attachment, sort_keys=True, ensure_ascii=False)


def _object_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _object_string_list(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _object_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _merge_string_lists(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            normalized = item.strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
    return merged


def _append_source_text(existing: str, incoming: str) -> str:
    incoming = incoming.strip()
    if not incoming:
        return existing
    if not existing:
        return incoming
    return f"{existing}\n\n---\n{incoming}"

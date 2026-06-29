import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.imports.spreadsheet_rows import (
    SpreadsheetRejectedRow,
    canonical_spreadsheet_column_name,
    parse_spreadsheet_rows,
)
from debug_agent.models.adapters import ModelAdapter, ModelResponse


DebugCaseField = Literal[
    "case_id",
    "task_type",
    "image_uri",
    "prompt",
    "golden_answer_json",
    "expected_output_json",
    "output_schema_json",
    "scoring_standard",
    "scoring_ops_json",
    "predictions_json",
    "score",
    "avg_score",
    "box_regions_json",
    "debug_status",
    "root_cause",
]


class SchemaFieldMapping(BaseModel):
    field: DebugCaseField
    source_column: str
    source_header: str
    source_value: object = ""
    confidence: float = Field(ge=0, le=1)
    reason: str


class SpreadsheetSchemaMappingResult(BaseModel):
    status: Literal["mapped", "missing_required", "invalid"]
    agent_mode: Literal["model", "deterministic", "fallback"] = "deterministic"
    validation_attempts: int = 0
    normalized_row: dict[str, object] = Field(default_factory=dict)
    mappings: dict[str, SchemaFieldMapping] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejected_row: SpreadsheetRejectedRow | None = None
    case: DebugCase | None = None
    model_provider: str = ""
    model_id: str = ""
    model_name: str = ""
    model_raw_output: str = ""
    model_error: str = ""


class _ColumnSignal(BaseModel):
    column: str
    header: str
    value: object
    value_text: str


class _Candidate(BaseModel):
    field: DebugCaseField
    signal: _ColumnSignal
    score: float
    reason: str


class SpreadsheetSchemaMappingAgent:
    """Case Intake Agent for turning arbitrary spreadsheet rows into DebugCase rows."""

    def __init__(self, *, model_adapter: ModelAdapter | None = None, model_error: str = "") -> None:
        self._model_adapter = model_adapter
        self._model_error = model_error

    async def map_row_with_model(
        self,
        *,
        headers: dict[str, str],
        values: dict[str, object],
        sheet_row_id: str,
        target_label: str = "",
        sample_rows: list[dict[str, object]] | None = None,
    ) -> SpreadsheetSchemaMappingResult:
        if self._model_adapter is None:
            if self._model_error:
                return SpreadsheetSchemaMappingResult(
                    status="invalid",
                    agent_mode="model",
                    model_error=self._model_error,
                    warnings=["Case Intake 模型不可用，未执行表结构理解。"],
                )
            deterministic = self.map_row(
                headers=headers,
                values=values,
                sheet_row_id=sheet_row_id,
                target_label=target_label,
                sample_rows=sample_rows,
            )
            deterministic.agent_mode = "deterministic"
            return deterministic

        previous_error = ""
        previous_output = ""
        last_result: SpreadsheetSchemaMappingResult | None = None
        for attempt in range(1, 4):
            prompt = _schema_mapping_prompt(
                headers=headers,
                values=values,
                sheet_row_id=sheet_row_id,
                target_label=target_label,
                sample_rows=sample_rows or [],
                previous_error=previous_error,
                previous_output=previous_output,
            )
            try:
                response = await self._model_adapter.generate(prompt=prompt, image_uri="")
            except Exception as exc:
                return SpreadsheetSchemaMappingResult(
                    status="invalid",
                    agent_mode="model",
                    validation_attempts=attempt,
                    model_error=str(exc),
                    warnings=["Case Intake 模型调用失败，未降级为规则成功路径。"],
                )
            mappings = _model_mappings_from_response(
                response=response,
                headers=headers,
                values=values,
            )
            if mappings:
                result = self._result_from_mappings(
                    mappings=mappings,
                    sheet_row_id=sheet_row_id,
                    candidates=self._rank_candidates(
                        signals=_column_signals(headers=headers, values=values),
                        target_label=target_label,
                        sample_rows=sample_rows or [],
                    ),
                )
                result.agent_mode = "model"
                result.model_provider = response.model_provider
                result.model_id = response.model_id
                result.model_name = response.model_name
                result.model_raw_output = response.raw_output
                result.validation_attempts = attempt
                if result.case is not None:
                    return result
                last_result = result
                previous_error = _schema_mapping_validation_error(result)
            else:
                last_result = SpreadsheetSchemaMappingResult(
                    status="invalid",
                    agent_mode="model",
                    validation_attempts=attempt,
                    model_provider=response.model_provider,
                    model_id=response.model_id,
                    model_name=response.model_name,
                    model_raw_output=response.raw_output,
                    model_error="model returned no usable mappings",
                    warnings=["Case Intake 模型未返回可用字段映射。"],
                )
                previous_error = "model returned no usable mappings; output must contain mappings with source_column."
            previous_output = response.raw_output
        if last_result is not None:
            last_result.warnings.append("Case Intake 模型自修后仍未产出合法 DebugCase。")
            return last_result
        return SpreadsheetSchemaMappingResult(
            status="invalid",
            agent_mode="model",
            model_error="case intake model did not run",
            warnings=["Case Intake 模型未执行。"],
        )

    def map_row(
        self,
        *,
        headers: dict[str, str],
        values: dict[str, object],
        sheet_row_id: str,
        target_label: str = "",
        sample_rows: list[dict[str, object]] | None = None,
    ) -> SpreadsheetSchemaMappingResult:
        signals = _column_signals(headers=headers, values=values)
        candidates = self._rank_candidates(
            signals=signals,
            target_label=target_label,
            sample_rows=sample_rows or [],
        )
        mappings = self._select_mappings(candidates)
        return self._result_from_mappings(
            mappings=mappings,
            sheet_row_id=sheet_row_id,
            candidates=candidates,
        )

    def _result_from_mappings(
        self,
        *,
        mappings: dict[str, SchemaFieldMapping],
        sheet_row_id: str,
        candidates: list[_Candidate],
    ) -> SpreadsheetSchemaMappingResult:
        mappings = _normalize_model_field_semantics(mappings)
        normalized_row = self._normalized_row(
            mappings=mappings,
            sheet_row_id=sheet_row_id,
        )
        missing_fields = _missing_required_fields(normalized_row)
        if missing_fields:
            return SpreadsheetSchemaMappingResult(
                status="missing_required",
                normalized_row=normalized_row,
                mappings={field: mapping for field, mapping in mappings.items()},
                missing_fields=missing_fields,
                warnings=_mapping_warnings(candidates=candidates, mappings=mappings),
            )

        parse_result = parse_spreadsheet_rows([normalized_row])
        if parse_result.imported_rows:
            return SpreadsheetSchemaMappingResult(
                status="mapped",
                normalized_row=normalized_row,
                mappings={field: mapping for field, mapping in mappings.items()},
                warnings=_mapping_warnings(candidates=candidates, mappings=mappings),
                case=parse_result.imported_rows[0].case,
            )
        rejected = parse_result.rejected_rows[0] if parse_result.rejected_rows else None
        return SpreadsheetSchemaMappingResult(
            status="invalid",
            normalized_row=normalized_row,
            mappings={field: mapping for field, mapping in mappings.items()},
            missing_fields=_missing_fields_from_rejection(rejected),
            warnings=_mapping_warnings(candidates=candidates, mappings=mappings),
            rejected_row=rejected,
        )

    def _rank_candidates(
        self,
        *,
        signals: list[_ColumnSignal],
        target_label: str,
        sample_rows: list[dict[str, object]],
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        for signal in signals:
            for field, score, reason in _field_scores(
                signal=signal,
                target_label=target_label,
                sample_rows=sample_rows,
            ):
                if score > 0:
                    candidates.append(
                        _Candidate(
                            field=field,
                            signal=signal,
                            score=score,
                            reason=reason,
                        )
                    )
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def _select_mappings(
        self,
        candidates: list[_Candidate],
    ) -> dict[str, SchemaFieldMapping]:
        mappings: dict[str, SchemaFieldMapping] = {}
        used_columns: set[str] = set()
        for candidate in candidates:
            field = candidate.field
            column = candidate.signal.column
            if field in mappings or column in used_columns:
                continue
            mappings[field] = SchemaFieldMapping(
                field=field,
                source_column=column,
                source_header=candidate.signal.header,
                source_value=candidate.signal.value,
                confidence=min(candidate.score / 100, 1.0),
                reason=candidate.reason,
            )
            used_columns.add(column)
        return mappings

    def _normalized_row(
        self,
        *,
        mappings: dict[str, SchemaFieldMapping],
        sheet_row_id: str,
    ) -> dict[str, object]:
        row: dict[str, object] = {"sheet_row_id": sheet_row_id}
        for field, mapping in mappings.items():
            row[field] = mapping_source_value(mapping)
        return row


def mapping_source_value(mapping: SchemaFieldMapping) -> object:
    return mapping.source_value


def _column_signals(
    *,
    headers: dict[str, str],
    values: dict[str, object],
) -> list[_ColumnSignal]:
    return [
        _ColumnSignal(
            column=column,
            header=header,
            value=values.get(column, ""),
            value_text=_stringify_cell(values.get(column, "")),
        )
        for column, header in headers.items()
        if header.strip()
    ]


def _schema_mapping_prompt(
    *,
    headers: dict[str, str],
    values: dict[str, object],
    sheet_row_id: str,
    target_label: str,
    sample_rows: list[dict[str, object]],
    previous_error: str = "",
    previous_output: str = "",
) -> str:
    repair_context = ""
    if previous_error:
        repair_context = (
            "\n上一次输出没有通过 validator。你必须修正后重新输出 JSON。"
            f"\nvalidator_error={previous_error}"
            f"\nprevious_output={previous_output[:2000]}\n"
        )
    return (
        "你是 Debug Agent 的 Case Intake / Schema Mapping Agent。"
        "你要理解任意用户表格的表头和目标行，把列映射到 DebugCase 字段。"
        "不要改写用户单元格内容，不要合并多个用户列。"
        "只输出 JSON object，不要 Markdown。输出字段："
        "mappings: object，key 必须是 DebugCase 字段名，value 包含 source_column, reason, confidence。"
        "可用字段名：case_id, task_type, image_uri, prompt, golden_answer_json, expected_output_json, "
        "output_schema_json, scoring_standard, scoring_ops_json, predictions_json, score, avg_score, "
        "box_regions_json, debug_status, root_cause。"
        "重要：普通任务的参考答案、标准答案、期望输出必须映射到 expected_output_json；"
        "golden_answer_json 只用于 OCR AnswerSet 结构，如 {\"answers\":[...]}。"
        "模型预测、模型回答、predict、actual output 必须映射到 predictions_json。"
        "source_column 必须使用列字母，例如 A、B、AA，不要使用表头名。"
        "如果多个列都像同一字段，请选最适合当前 debug 的一个，并在 reason 说明，不能合并。"
        "\n"
        f"sheet_row_id={sheet_row_id}\n"
        f"target_label={target_label}\n"
        f"headers={json.dumps(headers, ensure_ascii=False)}\n"
        f"target_row_values={json.dumps(values, ensure_ascii=False)}\n"
        f"sample_rows={json.dumps(sample_rows[:5], ensure_ascii=False)}\n"
        f"{repair_context}"
    )


def _model_mappings_from_response(
    *,
    response: ModelResponse,
    headers: dict[str, str],
    values: dict[str, object],
) -> dict[str, SchemaFieldMapping]:
    payload = _extract_json_object(response.raw_output)
    raw_mappings = payload.get("mappings")
    if not isinstance(raw_mappings, dict):
        return {}
    mappings: dict[str, SchemaFieldMapping] = {}
    for raw_field, raw_mapping in raw_mappings.items():
        field = _canonical_debug_field(str(raw_field).strip())
        if field is None or not isinstance(raw_mapping, dict):
            continue
        source_column = _resolve_source_column(raw_mapping=raw_mapping, headers=headers)
        if not source_column:
            continue
        confidence = raw_mapping.get("confidence")
        if not isinstance(confidence, int | float):
            confidence = 0.8
        mappings[field] = SchemaFieldMapping(
            field=field,
            source_column=source_column,
            source_header=headers[source_column],
            source_value=values.get(source_column, ""),
            confidence=max(0.0, min(float(confidence), 1.0)),
            reason=str(raw_mapping.get("reason") or "model selected this column"),
        )
    return mappings


def _resolve_source_column(
    *,
    raw_mapping: dict[object, object],
    headers: dict[str, str],
) -> str:
    raw = str(
        raw_mapping.get("source_column")
        or raw_mapping.get("column")
        or raw_mapping.get("source")
        or raw_mapping.get("source_header")
        or ""
    ).strip()
    if raw in headers:
        return raw
    normalized_raw = _normalize_text(raw)
    for column, header in headers.items():
        if _normalize_text(header) == normalized_raw:
            return column
    return ""


def _normalize_model_field_semantics(
    mappings: dict[str, SchemaFieldMapping],
) -> dict[str, SchemaFieldMapping]:
    normalized = dict(mappings)
    golden = normalized.get("golden_answer_json")
    if golden is not None and "expected_output_json" not in normalized:
        value = mapping_source_value(golden)
        if not _looks_like_answer_set(value):
            normalized.pop("golden_answer_json", None)
            normalized["expected_output_json"] = golden.model_copy(
                update={
                    "field": "expected_output_json",
                    "reason": (
                        golden.reason
                        + "；validator corrected non-OCR reference answer to expected_output_json"
                    ),
                }
            )
    return normalized


def _looks_like_answer_set(value: object) -> bool:
    try:
        payload = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and isinstance(payload.get("answers"), list)


def _schema_mapping_validation_error(result: SpreadsheetSchemaMappingResult) -> str:
    if result.missing_fields:
        return "missing required fields: " + ", ".join(result.missing_fields)
    if result.rejected_row is not None:
        return result.rejected_row.error_message
    if result.model_error:
        return result.model_error
    return f"mapping status={result.status}"


def _extract_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        try:
            payload = json.loads(fenced.group(1))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(stripped[start : end + 1])
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _field_scores(
    *,
    signal: _ColumnSignal,
    target_label: str,
    sample_rows: list[dict[str, object]],
) -> list[tuple[DebugCaseField, float, str]]:
    header = _normalize_text(signal.header)
    value_text = signal.value_text.strip()
    canonical = canonical_spreadsheet_column_name(signal.header)
    scores: list[tuple[DebugCaseField, float, str]] = []
    exact_field = _canonical_debug_field(canonical)
    if exact_field:
        scores.append((exact_field, 96, f"表头已是后端字段 {exact_field}"))

    if _matches_target(value_text, target_label):
        scores.append(("case_id", 98, "目标行标识与用户指定的样本 ID 一致"))
    elif _has_any(header, ("case", "sample", "样本", "编号", "标识", "id")) and _looks_like_identifier(value_text):
        scores.append(("case_id", 72, "表头和值都像样本标识"))

    if _has_any(header, ("prompt", "query", "question", "instruction", "用户", "提示", "问题", "指令", "输入")):
        scores.append(("prompt", 82, "表头表达用户输入或 prompt"))

    if _has_any(header, ("expected", "reference", "golden", "answer", "正确", "期望", "参考", "答案", "标答")):
        scores.append(("expected_output_json", 86, "表头表达参考答案或期望输出"))

    if _has_any(header, ("predict", "prediction", "actual", "observed", "模型输出", "预测", "识别结果", "输出")):
        scores.append(("predictions_json", 86, "表头表达模型输出或预测结果"))
    if _has_any(header, ("模型回答", "模型结果")) or (
        _has_any(header, ("模型", "model")) and _has_any(header, ("回答", "结果", "answer", "response"))
    ):
        scores.append(("predictions_json", 84, "表头表达模型回答"))

    if _looks_like_media(value_text) or _has_any(header, ("video", "image", "media", "file", "图片", "视频", "素材", "文件")):
        scores.append(("image_uri", 84 if _looks_like_media(value_text) else 70, "列值或表头表达媒体输入"))

    if _looks_like_scoring_ops(value_text) or _has_any(header, ("chains", "ops", "evalop", "评测链", "打分链")):
        scores.append(("scoring_ops_json", 92, "列值或表头表达结构化评分算子"))

    if _has_any(header, ("scoring", "rubric", "score rule", "judge", "评分", "打分", "判分", "标准", "规则")):
        score = 82
        if _has_any(header, ("详细", "严格", "strict", "full", "detail")):
            score += 8
        if _has_any(value_text.lower(), ("0分", "1分", "score", "must", "必须", "满足")):
            score += 6
        scores.append(("scoring_standard", score, "表头和值表达自然语言评分规则"))

    if canonical in {"score", "avg_score"} or _has_any(header, ("score", "分数", "得分")) and _looks_like_score(value_text):
        scores.append(("score", 84, "表头和值表达已有评分"))

    if _has_any(header, ("task_type", "task type", "任务类型")):
        scores.append(("task_type", 92, "表头表达任务类型"))

    if _has_any(header, ("schema", "输出结构", "格式约束")):
        scores.append(("output_schema_json", 78, "表头表达输出 schema"))

    if _has_any(header, ("debug_status", "状态")):
        scores.append(("debug_status", 76, "表头表达 debug 状态"))

    if _has_any(header, ("root cause", "gpt_response", "feedback", "problem", "错误", "原因", "反馈", "评估问题")):
        scores.append(("root_cause", 78, "表头表达评估反馈或问题原因"))

    del sample_rows
    return scores


def _canonical_debug_field(canonical: str) -> DebugCaseField | None:
    fields: set[str] = {
        "case_id",
        "task_type",
        "image_uri",
        "prompt",
        "golden_answer_json",
        "expected_output_json",
        "output_schema_json",
        "scoring_standard",
        "scoring_ops_json",
        "predictions_json",
        "score",
        "avg_score",
        "box_regions_json",
        "debug_status",
        "root_cause",
    }
    return canonical if canonical in fields else None  # type: ignore[return-value]


def _missing_required_fields(row: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for field in ("case_id", "prompt", "expected_output_json", "predictions_json"):
        if not _stringify_cell(row.get(field, "")).strip():
            missing.append(field)
    if not (
        _stringify_cell(row.get("scoring_standard", "")).strip()
        or _stringify_cell(row.get("scoring_ops_json", "")).strip()
    ):
        missing.append("scoring_standard")
    return missing


def _mapping_warnings(
    *,
    candidates: list[_Candidate],
    mappings: dict[str, SchemaFieldMapping],
) -> list[str]:
    warnings: list[str] = []
    for field, mapping in mappings.items():
        field_candidates = [
            item for item in candidates if item.field == field and item.signal.column != mapping.source_column
        ]
        if field_candidates:
            alternatives = ", ".join(
                f"{item.signal.column}:{item.signal.header}" for item in field_candidates[:3]
            )
            warnings.append(f"{field} 还有候选列未采用：{alternatives}")
    return warnings


def _missing_fields_from_rejection(rejected: SpreadsheetRejectedRow | None) -> list[str]:
    if rejected is None:
        return []
    return re.findall(
        r"Missing required spreadsheet row value: ([A-Za-z0-9_]+)",
        rejected.error_message,
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s_\-：:=（）()\\[\\]【】]+", "", value.strip().lower())


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    normalized = _normalize_text(value)
    return any(_normalize_text(item) in normalized for item in needles)


def _matches_target(value: str, target_label: str) -> bool:
    target = re.sub(r"\s+", "", target_label.strip().lower())
    candidate = re.sub(r"\s+", "", value.strip().lower())
    return bool(target and target in candidate)


def _looks_like_identifier(value: str) -> bool:
    return bool(re.search(r"\b[A-Za-z][A-Za-z0-9]{1,12}[-_]\d{1,10}\b", value.strip()))


def _looks_like_media(value: str) -> bool:
    stripped = value.strip().lower().split("?", 1)[0]
    return stripped.startswith(("http://", "https://", "file://", "tos://", "data:")) or stripped.endswith(
        (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".png", ".jpg", ".jpeg", ".webp")
    )


def _looks_like_score(value: str) -> bool:
    stripped = value.strip()
    return bool(re.fullmatch(r"\[?[-+]?\d+(\.\d+)?\]?", stripped))


def _looks_like_scoring_ops(value: str) -> bool:
    try:
        payload = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, list):
        return False
    return any(isinstance(item, dict) and ("op_name" in item or "operator" in item) for item in payload)


def _stringify_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

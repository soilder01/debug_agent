import csv
import json
from io import StringIO

from pydantic import BaseModel, ValidationError

from debug_agent.cases.models import AnswerSet, BoxRegion, DebugCase, HumanNotes, Prediction


COLUMN_ALIASES: dict[str, str] = {
    "case_id": "case_id",
    "case id": "case_id",
    "样本ID": "case_id",
    "样本 ID": "case_id",
    "样本编号": "case_id",
    "image_uri": "image_uri",
    "image_url": "image_uri",
    "image url": "image_uri",
    "图片": "image_uri",
    "图片链接": "image_uri",
    "图片URL": "image_uri",
    "prompt": "prompt",
    "提示词": "prompt",
    "模型输入": "prompt",
    "题目prompt": "prompt",
    "golden_answer_json": "golden_answer_json",
    "golden answer json": "golden_answer_json",
    "标答JSON": "golden_answer_json",
    "标准答案JSON": "golden_answer_json",
    "scoring_standard": "scoring_standard",
    "scoring standard": "scoring_standard",
    "评分标准": "scoring_standard",
    "打分标准": "scoring_standard",
    "predictions_json": "predictions_json",
    "predictions json": "predictions_json",
    "预测JSON": "predictions_json",
    "模型预测JSON": "predictions_json",
    "模型输出JSON": "predictions_json",
    "avg_score": "avg_score",
    "avg score": "avg_score",
    "平均分": "avg_score",
    "box_regions_json": "box_regions_json",
    "box regions json": "box_regions_json",
    "区域JSON": "box_regions_json",
    "框坐标JSON": "box_regions_json",
    "box_region_box_id": "box_region_box_id",
    "box region box id": "box_region_box_id",
    "box_id": "box_region_box_id",
    "框ID": "box_region_box_id",
    "box_region_x": "box_region_x",
    "box region x": "box_region_x",
    "x": "box_region_x",
    "box_region_y": "box_region_y",
    "box region y": "box_region_y",
    "y": "box_region_y",
    "box_region_width": "box_region_width",
    "box region width": "box_region_width",
    "width": "box_region_width",
    "box_region_height": "box_region_height",
    "box region height": "box_region_height",
    "height": "box_region_height",
    "box_region_label": "box_region_label",
    "box region label": "box_region_label",
    "region label": "box_region_label",
    "区域标签": "box_region_label",
    "debug_status": "debug_status",
    "debug status": "debug_status",
    "debug状态": "debug_status",
    "状态": "debug_status",
    "root_cause": "root_cause",
    "root cause": "root_cause",
    "错误原因": "root_cause",
    "根因": "root_cause",
}


class CsvRejectedRow(BaseModel):
    row_number: int
    error_message: str


class CsvCaseParseResult(BaseModel):
    cases: list[DebugCase]
    rejected_rows: list[CsvRejectedRow]


def parse_csv_cases(csv_text: str) -> CsvCaseParseResult:
    cases: list[DebugCase] = []
    rejected_rows: list[CsvRejectedRow] = []
    reader = csv.DictReader(StringIO(csv_text))
    for row_number, row in enumerate(reader, start=2):
        try:
            cases.append(_row_to_case(_normalize_row_columns(row)))
        except (KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            rejected_rows.append(CsvRejectedRow(row_number=row_number, error_message=str(exc)))
    return CsvCaseParseResult(cases=cases, rejected_rows=rejected_rows)


def _row_to_case(row: dict[str, str | None]) -> DebugCase:
    golden_answer_text = _required(row, "golden_answer_json")
    predictions_text = _required(row, "predictions_json")
    return DebugCase(
        case_id=_required(row, "case_id"),
        image_uri=_required(row, "image_uri"),
        prompt=_required(row, "prompt"),
        golden_answer=AnswerSet.model_validate(_loads_json(golden_answer_text, "golden_answer_json")),
        scoring_standard=_required(row, "scoring_standard"),
        predictions=[
            Prediction.model_validate(item) for item in _loads_json_list(predictions_text, "predictions_json")
        ],
        avg_score=float(_required(row, "avg_score")),
        box_regions=_parse_box_regions(row),
        human_notes=HumanNotes(
            debug_status=row.get("debug_status") or "",
            root_cause=row.get("root_cause") or "",
        ),
    )


def _parse_box_regions(row: dict[str, str | None]) -> list[BoxRegion]:
    json_regions = _loads_optional_json_list(row.get("box_regions_json"), "box_regions_json")
    if json_regions:
        return [BoxRegion.model_validate(item) for item in json_regions]
    flat_region = _parse_flat_box_region(row)
    if flat_region is None:
        return []
    return [flat_region]


def _parse_flat_box_region(row: dict[str, str | None]) -> BoxRegion | None:
    required_keys = [
        "box_region_box_id",
        "box_region_x",
        "box_region_y",
        "box_region_width",
        "box_region_height",
    ]
    if not any(row.get(key) for key in required_keys):
        return None
    missing_keys = [key for key in required_keys if not row.get(key)]
    if missing_keys:
        raise ValueError(f"Missing required flat box region column value: {', '.join(missing_keys)}")
    return BoxRegion(
        box_id=int(_required(row, "box_region_box_id")),
        x=int(_required(row, "box_region_x")),
        y=int(_required(row, "box_region_y")),
        width=int(_required(row, "box_region_width")),
        height=int(_required(row, "box_region_height")),
        label=row.get("box_region_label") or "",
    )


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required CSV column value: {key}")
    return value


def _canonical_column_name(column_name: str) -> str:
    stripped = column_name.strip()
    return COLUMN_ALIASES.get(stripped, stripped)


def _normalize_row_columns(row: dict[str, str | None]) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    source_columns: dict[str, str] = {}
    for column_name, value in row.items():
        canonical_name = _canonical_column_name(column_name)
        if canonical_name in normalized:
            previous_column = source_columns[canonical_name]
            raise ValueError(
                f"Duplicate CSV columns for {canonical_name}: {previous_column}, {column_name}"
            )
        normalized[canonical_name] = value
        source_columns[canonical_name] = column_name
    return normalized


def _loads_json(value: str, key: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {key}: {value}") from exc


def _loads_json_list(value: str, key: str) -> list[object]:
    loaded = _loads_json(value, key)
    if not isinstance(loaded, list):
        raise ValueError(f"Expected JSON list in {key}: {value}")
    return loaded


def _loads_optional_json_list(value: str | None, key: str) -> list[object]:
    if value is None or value == "":
        return []
    return _loads_json_list(value, key)

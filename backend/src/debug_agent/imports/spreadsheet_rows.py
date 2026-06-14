import json

from pydantic import BaseModel, ValidationError

from debug_agent.cases.models import AnswerSet, BoxRegion, DebugCase, HumanNotes, Prediction
from debug_agent.imports.csv_cases import COLUMN_ALIASES


class SpreadsheetImportedRow(BaseModel):
    sheet_row_id: str
    case: DebugCase


class SpreadsheetRejectedRow(BaseModel):
    row_index: int
    sheet_row_id: str
    error_message: str


class SpreadsheetRowImportResult(BaseModel):
    imported_rows: list[SpreadsheetImportedRow]
    rejected_rows: list[SpreadsheetRejectedRow]


def parse_spreadsheet_rows(rows: list[dict[str, object]]) -> SpreadsheetRowImportResult:
    imported_rows: list[SpreadsheetImportedRow] = []
    rejected_rows: list[SpreadsheetRejectedRow] = []
    for row_index, row in enumerate(rows):
        normalized_row = _normalize_row_columns(row)
        sheet_row_id = _optional_string(normalized_row.get("sheet_row_id"))
        try:
            imported_rows.append(
                SpreadsheetImportedRow(
                    sheet_row_id=sheet_row_id,
                    case=_row_to_case(normalized_row),
                )
            )
        except (KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            rejected_rows.append(
                SpreadsheetRejectedRow(
                    row_index=row_index,
                    sheet_row_id=sheet_row_id,
                    error_message=str(exc),
                )
            )
    return SpreadsheetRowImportResult(imported_rows=imported_rows, rejected_rows=rejected_rows)


def _row_to_case(row: dict[str, object]) -> DebugCase:
    return DebugCase(
        case_id=_required_string(row, "case_id"),
        task_type=_optional_string(row.get("task_type")) or "handwriting_ocr",
        image_uri=_optional_string(row.get("image_uri")),
        prompt=_required_string(row, "prompt"),
        golden_answer=AnswerSet.model_validate(_loads_json_value(_required(row, "golden_answer_json"), "golden_answer_json")),
        expected_output=_loads_optional_json_object(row.get("expected_output_json"), "expected_output_json"),
        output_schema=_loads_optional_json_object(row.get("output_schema_json"), "output_schema_json"),
        scoring_standard=_required_string(row, "scoring_standard"),
        predictions=[
            Prediction.model_validate(item)
            for item in _loads_json_list(_required(row, "predictions_json"), "predictions_json")
        ],
        avg_score=_required_float(row, "avg_score"),
        box_regions=_parse_box_regions(row),
        human_notes=HumanNotes(
            debug_status=_optional_string(row.get("debug_status")),
            root_cause=_optional_string(row.get("root_cause")),
        ),
    )


def _parse_box_regions(row: dict[str, object]) -> list[BoxRegion]:
    regions = _loads_optional_json_list(row.get("box_regions_json"), "box_regions_json")
    return [BoxRegion.model_validate(item) for item in regions]


def _required(row: dict[str, object], key: str) -> object:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required spreadsheet row value: {key}")
    return value


def _required_string(row: dict[str, object], key: str) -> str:
    return str(_required(row, key))


def _required_float(row: dict[str, object], key: str) -> float:
    value = _required(row, key)
    if not isinstance(value, (str, int, float)):
        raise ValueError(f"Expected numeric spreadsheet row value: {key}")
    return float(value)


def _optional_string(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _loads_json_value(value: object, key: str) -> object:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {key}: {value}") from exc
    return value


def _loads_json_list(value: object, key: str) -> list[object]:
    loaded = _loads_json_value(value, key)
    if not isinstance(loaded, list):
        raise ValueError(f"Expected JSON list in {key}: {value}")
    return loaded


def _loads_optional_json_list(value: object, key: str) -> list[object]:
    if value is None or value == "":
        return []
    return _loads_json_list(value, key)


def _loads_optional_json_object(value: object, key: str) -> dict[str, object]:
    if value is None or value == "":
        return {}
    loaded = _loads_json_value(value, key)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in {key}: {value}")
    return loaded


def _normalize_row_columns(row: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    source_columns: dict[str, str] = {}
    for column_name, value in row.items():
        canonical_name = _canonical_column_name(column_name)
        if canonical_name in normalized:
            previous_column = source_columns[canonical_name]
            raise ValueError(
                f"Duplicate spreadsheet row columns for {canonical_name}: {previous_column}, {column_name}"
            )
        normalized[canonical_name] = value
        source_columns[canonical_name] = column_name
    return normalized


def _canonical_column_name(column_name: str) -> str:
    stripped = column_name.strip()
    if stripped in {"sheet_row_id", "row_id", "row id", "飞书行ID", "表格行ID"}:
        return "sheet_row_id"
    return COLUMN_ALIASES.get(stripped, stripped)

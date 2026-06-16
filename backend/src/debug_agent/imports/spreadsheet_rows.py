import json

from pydantic import BaseModel, ValidationError

from debug_agent.cases.models import AnswerSet, BoxRegion, DebugCase, HumanNotes, Prediction
from debug_agent.cases.comparator import parse_video_detection_output
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
    task_type = _optional_string(row.get("task_type")) or _infer_task_type(row)
    expected_output = _load_expected_output(row, task_type=task_type)
    scoring_standard = _optional_string(row.get("scoring_ops_json")) or _required_string(row, "scoring_standard")
    return DebugCase(
        case_id=_required_string(row, "case_id"),
        task_type=task_type,
        image_uri=_optional_string(row.get("image_uri")),
        prompt=_required_string(row, "prompt"),
        golden_answer=_load_golden_answer(row, task_type=task_type, expected_output=expected_output),
        expected_output=expected_output,
        output_schema=_loads_optional_json_object(row.get("output_schema_json"), "output_schema_json"),
        scoring_standard=scoring_standard,
        predictions=_load_predictions(row),
        avg_score=_row_score(row),
        box_regions=_parse_box_regions(row),
        human_notes=HumanNotes(
            debug_status=_optional_string(row.get("debug_status")),
            root_cause=_optional_string(row.get("root_cause")),
        ),
    )


def _infer_task_type(row: dict[str, object]) -> str:
    if row.get("scoring_ops_json") or _optional_string(row.get("image_uri")).lower().endswith(".mp4"):
        return "video_detection"
    return "handwriting_ocr"


def _load_expected_output(row: dict[str, object], *, task_type: str) -> dict[str, object]:
    expected_output = _loads_optional_json_object(row.get("expected_output_json"), "expected_output_json")
    if task_type == "video_detection" and "video_action_segments" in expected_output:
        return parse_video_detection_output(json.dumps(expected_output)).model_dump()
    return expected_output


def _load_predictions(row: dict[str, object]) -> list[Prediction]:
    raw_predictions = _loads_json_list(_required(row, "predictions_json"), "predictions_json")
    scores = _score_values(row.get("score"))
    predictions: list[Prediction] = []
    for index, item in enumerate(raw_predictions):
        if isinstance(item, str):
            predictions.append(Prediction(trial=index + 1, raw_output=item, score=_score_for_index(scores, index)))
        else:
            predictions.append(Prediction.model_validate(item))
    return predictions


def _row_score(row: dict[str, object]) -> float:
    value = row.get("avg_score")
    if value is not None and value != "":
        return _required_float(row, "avg_score")
    scores = _score_values(row.get("score"))
    if scores:
        return sum(scores) / len(scores)
    return 0.0


def _score_values(value: object) -> list[int]:
    if value is None or value == "":
        return []
    loaded = _loads_json_value(value, "score")
    if isinstance(loaded, list):
        return [int(item) for item in loaded if isinstance(item, int | float | str) and str(item).strip()]
    if isinstance(loaded, int | float | str) and str(loaded).strip():
        return [int(loaded)]
    return []


def _score_for_index(scores: list[int], index: int) -> int:
    if not scores:
        return 0
    return scores[min(index, len(scores) - 1)]


def _load_golden_answer(
    row: dict[str, object],
    *,
    task_type: str,
    expected_output: dict[str, object],
) -> AnswerSet:
    value = row.get("golden_answer_json")
    if value is not None and value != "":
        return AnswerSet.model_validate(_loads_json_value(value, "golden_answer_json"))
    if task_type == "handwriting_ocr" or not expected_output:
        raise ValueError("Missing required spreadsheet row value: golden_answer_json")
    return AnswerSet(answers=[])


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

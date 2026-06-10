import csv
import json
from io import StringIO

from pydantic import BaseModel, ValidationError

from debug_agent.cases.models import AnswerSet, DebugCase, HumanNotes, Prediction


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
            cases.append(_row_to_case(row))
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
        human_notes=HumanNotes(
            debug_status=row.get("debug_status") or "",
            root_cause=row.get("root_cause") or "",
        ),
    )


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required CSV column value: {key}")
    return value


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

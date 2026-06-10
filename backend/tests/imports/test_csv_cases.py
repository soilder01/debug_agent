import csv
import io
import json

from debug_agent.imports.csv_cases import parse_csv_cases


def csv_text(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
            "debug_status",
            "root_cause",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def test_parse_csv_cases_maps_rows_to_debug_cases() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]

    result = parse_csv_cases(
        csv_text(
            [
                {
                    "case_id": "csv-1",
                    "image_uri": "file://image.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": json.dumps(golden_answer),
                    "scoring_standard": "exact match",
                    "predictions_json": json.dumps(predictions),
                    "avg_score": "1.0",
                    "debug_status": "pending",
                    "root_cause": "",
                }
            ]
        )
    )

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    case = result.cases[0]
    assert case.case_id == "csv-1"
    assert case.golden_answer.answers[0].student_answer == "42"
    assert case.predictions[0].raw_output == raw_output
    assert case.avg_score == 1.0
    assert case.human_notes.debug_status == "pending"


def test_parse_csv_cases_reports_invalid_rows() -> None:
    result = parse_csv_cases(
        csv_text(
            [
                {
                    "case_id": "bad-csv",
                    "image_uri": "file://image.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": "not-json",
                    "scoring_standard": "exact match",
                    "predictions_json": "[]",
                    "avg_score": "0.0",
                    "debug_status": "",
                    "root_cause": "",
                }
            ]
        )
    )

    assert result.cases == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].row_number == 2
    assert "not-json" in result.rejected_rows[0].error_message

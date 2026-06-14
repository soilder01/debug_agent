import json

from debug_agent.imports.spreadsheet_rows import parse_spreadsheet_rows


def test_parse_spreadsheet_rows_maps_rows_to_debug_cases_and_preserves_row_id() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    predictions = [{"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1}]

    result = parse_spreadsheet_rows(
        [
            {
                "sheet_row_id": "row-001",
                "case_id": "sheet-case-1",
                "image_uri": "file://sheet.png",
                "prompt": "Read the handwritten answer",
                "golden_answer_json": golden_answer,
                "scoring_standard": "exact match",
                "predictions_json": predictions,
                "avg_score": 1.0,
                "debug_status": "pending",
                "root_cause": "needs_debug",
            }
        ]
    )

    assert result.rejected_rows == []
    assert len(result.imported_rows) == 1
    imported = result.imported_rows[0]
    assert imported.sheet_row_id == "row-001"
    assert imported.case.case_id == "sheet-case-1"
    assert imported.case.golden_answer.answers[0].student_answer == "42"
    assert imported.case.predictions[0].score == 1
    assert imported.case.avg_score == 1.0
    assert imported.case.human_notes.debug_status == "pending"
    assert imported.case.human_notes.root_cause == "needs_debug"


def test_parse_spreadsheet_rows_imports_task_native_expected_output() -> None:
    result = parse_spreadsheet_rows(
        [
            {
                "sheet_row_id": "row-classification-native",
                "case_id": "sheet-classification-native",
                "task_type": "classification",
                "image_uri": "",
                "prompt": "Classify sentiment and return JSON.",
                "golden_answer_json": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
                "expected_output_json": {"label": "positive"},
                "output_schema_json": {"type": "object", "required": ["label"]},
                "scoring_standard": "label must match exactly.",
                "predictions_json": [{"trial": 1, "raw_output": "{\"label\":\"negative\"}", "score": 0}],
                "avg_score": 0.0,
            }
        ]
    )

    assert result.rejected_rows == []
    case = result.imported_rows[0].case
    assert case.task_type == "classification"
    assert case.expected_output == {"label": "positive"}
    assert case.output_schema == {"type": "object", "required": ["label"]}


def test_parse_spreadsheet_rows_imports_non_ocr_expected_output_without_golden_answer_json() -> None:
    result = parse_spreadsheet_rows(
        [
            {
                "sheet_row_id": "row-video-native-no-golden",
                "case_id": "sheet-video-native-no-golden",
                "task_type": "video_detection",
                "image_uri": "file:///tmp/video-native.mp4",
                "prompt": "Detect events and return temporal segment JSON.",
                "expected_output_json": {
                    "temporal_segments": [
                        {
                            "target_id": "video:segment:1",
                            "start_ms": 1000,
                            "end_ms": 2500,
                            "label": "person_enters",
                        }
                    ]
                },
                "output_schema_json": {"type": "object", "required": ["temporal_segments"]},
                "scoring_standard": "temporal segment target ids and labels must match.",
                "predictions_json": [
                    {
                        "trial": 1,
                        "raw_output": (
                            "{\"temporal_segments\":[{\"target_id\":\"video:segment:1\","
                            "\"start_ms\":1000,\"end_ms\":2500,\"label\":\"person_leaves\"}]}"
                        ),
                        "score": 0,
                    }
                ],
                "avg_score": 0.0,
            }
        ]
    )

    assert result.rejected_rows == []
    case = result.imported_rows[0].case
    assert case.task_type == "video_detection"
    assert case.expected_output["temporal_segments"][0]["target_id"] == "video:segment:1"
    assert case.golden_answer.answers == []


def test_parse_spreadsheet_rows_accepts_box_regions_json() -> None:
    result = parse_spreadsheet_rows(
        [
            {
                "sheet_row_id": "row-002",
                "case_id": "sheet-case-2",
                "image_uri": "file://sheet-region.png",
                "prompt": "Read the handwritten answer",
                "golden_answer_json": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
                "scoring_standard": "exact match",
                "predictions_json": [
                    {
                        "trial": 1,
                        "raw_output": json.dumps({"answers": [{"box_id": 7, "student_answer": "低温烘干"}]}),
                        "score": 0,
                    }
                ],
                "avg_score": 0.0,
                "box_regions_json": [
                    {
                        "box_id": 7,
                        "x": 12,
                        "y": 34,
                        "width": 56,
                        "height": 78,
                        "unit": "pixel",
                        "label": "answer 7",
                    }
                ],
            }
        ]
    )

    assert result.rejected_rows == []
    region = result.imported_rows[0].case.box_regions[0]
    assert region.box_id == 7
    assert region.x == 12
    assert region.label == "answer 7"


def test_parse_spreadsheet_rows_reports_invalid_rows_with_row_id() -> None:
    result = parse_spreadsheet_rows(
        [
            {
                "sheet_row_id": "row-bad",
                "case_id": "bad-case",
                "image_uri": "file://bad.png",
                "prompt": "Read",
                "golden_answer_json": "not-json",
                "scoring_standard": "exact match",
                "predictions_json": [],
                "avg_score": 0.0,
            }
        ]
    )

    assert result.imported_rows == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].sheet_row_id == "row-bad"
    assert result.rejected_rows[0].row_index == 0
    assert "Invalid JSON in golden_answer_json" in result.rejected_rows[0].error_message

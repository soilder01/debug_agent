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


def test_parse_csv_cases_imports_task_native_expected_output() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "positive"}]}
    predictions = [{"trial": 1, "raw_output": "{\"label\":\"negative\"}", "score": 0}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "task_type",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "expected_output_json",
            "output_schema_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-classification-native",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer_json": json.dumps(golden_answer),
            "expected_output_json": json.dumps({"label": "positive"}),
            "output_schema_json": json.dumps({"type": "object", "required": ["label"]}),
            "scoring_standard": "label must match exactly.",
            "predictions_json": json.dumps(predictions),
            "avg_score": "0.0",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    case = result.cases[0]
    assert case.task_type == "classification"
    assert case.expected_output == {"label": "positive"}
    assert case.output_schema == {"type": "object", "required": ["label"]}


def test_parse_csv_cases_imports_non_ocr_expected_output_without_golden_answer_json() -> None:
    predictions = [
        {
            "trial": 1,
            "raw_output": (
                "{\"regions\":[{\"target_id\":\"image:region:1\",\"x\":10,\"y\":20,"
                "\"width\":30,\"height\":40,\"label\":\"dog\"}]}"
            ),
            "score": 0,
        }
    ]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "task_type",
            "image_uri",
            "prompt",
            "expected_output_json",
            "output_schema_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-image-native-no-golden",
            "task_type": "image_detection",
            "image_uri": "file:///tmp/image-native.png",
            "prompt": "Detect animals and return region JSON.",
            "expected_output_json": json.dumps(
                {
                    "regions": [
                        {"target_id": "image:region:1", "x": 10, "y": 20, "width": 30, "height": 40, "label": "cat"}
                    ]
                }
            ),
            "output_schema_json": json.dumps({"type": "object", "required": ["regions"]}),
            "scoring_standard": "region target ids and labels must match.",
            "predictions_json": json.dumps(predictions),
            "avg_score": "0.0",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    case = result.cases[0]
    assert case.task_type == "image_detection"
    assert case.expected_output["regions"][0]["target_id"] == "image:region:1"
    assert case.golden_answer.answers == []


def test_parse_csv_cases_imports_box_regions_json() -> None:
    golden_answer = {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]}
    raw_output = json.dumps({"answers": [{"box_id": 7, "student_answer": "低温烘干"}]})
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 0}]
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
            "box_regions_json",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-region-1",
            "image_uri": "file://region.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "0.0",
            "box_regions_json": json.dumps(
                [
                    {
                        "box_id": 7,
                        "x": 12,
                        "y": 34,
                        "width": 56,
                        "height": 78,
                        "unit": "pixel",
                        "label": "box-7",
                    }
                ]
            ),
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    assert result.cases[0].box_regions[0].box_id == 7
    assert result.cases[0].box_regions[0].x == 12
    assert result.cases[0].box_regions[0].label == "box-7"


def test_parse_csv_cases_imports_flat_box_region_columns() -> None:
    golden_answer = {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]}
    raw_output = json.dumps({"answers": [{"box_id": 7, "student_answer": "低温烘干"}]})
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 0}]
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
            "box_region_box_id",
            "box_region_x",
            "box_region_y",
            "box_region_width",
            "box_region_height",
            "box_region_label",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-flat-region-1",
            "image_uri": "file://region.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "0.0",
            "box_region_box_id": "7",
            "box_region_x": "12",
            "box_region_y": "34",
            "box_region_width": "56",
            "box_region_height": "78",
            "box_region_label": "box-7",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    assert result.cases[0].box_regions[0].box_id == 7
    assert result.cases[0].box_regions[0].x == 12
    assert result.cases[0].box_regions[0].y == 34
    assert result.cases[0].box_regions[0].width == 56
    assert result.cases[0].box_regions[0].height == 78
    assert result.cases[0].box_regions[0].label == "box-7"


def test_parse_csv_cases_rejects_incomplete_flat_box_region_columns() -> None:
    golden_answer = {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]}
    raw_output = json.dumps({"answers": [{"box_id": 7, "student_answer": "低温烘干"}]})
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 0}]
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
            "box_region_box_id",
            "box_region_x",
            "box_region_y",
            "box_region_width",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-flat-region-bad",
            "image_uri": "file://region.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "0.0",
            "box_region_box_id": "7",
            "box_region_x": "12",
            "box_region_y": "34",
            "box_region_width": "56",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.cases == []
    assert len(result.rejected_rows) == 1
    assert "box_region_height" in result.rejected_rows[0].error_message


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


def test_parse_csv_cases_accepts_table_column_aliases() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "84"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "样本ID",
            "图片链接",
            "提示词",
            "标答JSON",
            "评分标准",
            "模型预测JSON",
            "平均分",
            "debug状态",
            "错误原因",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "样本ID": "alias-csv-1",
            "图片链接": "file://alias.png",
            "提示词": "Read the handwritten answer",
            "标答JSON": json.dumps(golden_answer),
            "评分标准": "exact match",
            "模型预测JSON": json.dumps(predictions),
            "平均分": "1.0",
            "debug状态": "pending",
            "错误原因": "visual_recognition_failure",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    case = result.cases[0]
    assert case.case_id == "alias-csv-1"
    assert case.image_uri == "file://alias.png"
    assert case.golden_answer.answers[0].student_answer == "84"
    assert case.predictions[0].raw_output == raw_output
    assert case.human_notes.debug_status == "pending"
    assert case.human_notes.root_cause == "visual_recognition_failure"


def test_parse_csv_cases_rejects_duplicate_alias_columns() -> None:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "样本ID",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "canonical-id",
            "样本ID": "alias-id",
            "image_uri": "file://image.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps({"answers": [{"box_id": 1, "student_answer": "42"}]}),
            "scoring_standard": "exact match",
            "predictions_json": "[]",
            "avg_score": "0.0",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.cases == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].row_number == 2
    assert "Duplicate CSV columns for case_id" in result.rejected_rows[0].error_message

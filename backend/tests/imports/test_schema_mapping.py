import asyncio
import json

from debug_agent.imports.schema_mapping import SpreadsheetSchemaMappingAgent
from debug_agent.models.fake import FakeModelAdapter


def test_schema_mapping_agent_maps_non_standard_headers_to_debug_case() -> None:
    result = SpreadsheetSchemaMappingAgent().map_row(
        headers={
            "A": "样本编号",
            "B": "用户问题",
            "C": "模型回答",
            "D": "标准答案",
            "E": "判分规则",
            "F": "素材文件",
        },
        values={
            "A": "CASE-42",
            "B": "Read the image and return JSON.",
            "C": '{"answer":"3"}',
            "D": '{"answer":"8"}',
            "E": "answer must match exactly",
            "F": "case-42.png",
        },
        sheet_row_id="2",
        target_label="CASE-42",
    )

    assert result.status == "mapped"
    assert result.case is not None
    assert result.case.case_id == "CASE-42"
    assert result.case.prompt == "Read the image and return JSON."
    assert result.case.image_uri == "case-42.png"
    assert result.case.predictions[0].raw_output == '{"answer":"3"}'
    assert result.mappings["expected_output_json"].source_header == "标准答案"


def test_schema_mapping_agent_uses_model_mapping_before_fallback_rules() -> None:
    output = {
        "mappings": {
            "case_id": {"source_column": "A", "confidence": 0.98, "reason": "explicit row id"},
            "prompt": {"source_column": "B", "confidence": 0.95, "reason": "user prompt"},
            "predictions_json": {"source_column": "C", "confidence": 0.94, "reason": "observed output"},
            "expected_output_json": {"source_column": "D", "confidence": 0.94, "reason": "reference answer"},
            "scoring_standard": {"source_column": "F", "confidence": 0.91, "reason": "user asked for loose rubric"},
        }
    }
    agent = SpreadsheetSchemaMappingAgent(
        model_adapter=FakeModelAdapter(outputs=[json.dumps(output)], model_name="fake-seedpro")
    )

    result = asyncio.run(
        agent.map_row_with_model(
            headers={
                "A": "id",
                "B": "user prompt",
                "C": "predict",
                "D": "参考答案",
                "E": "评分标准（详细版）",
                "F": "评分标准（宽松版）",
            },
            values={
                "A": "CASE-77",
                "B": "Return JSON.",
                "C": '{"answer":"bad"}',
                "D": '{"answer":"good"}',
                "E": "详细标准",
                "F": "宽松标准",
            },
            sheet_row_id="7",
            target_label="CASE-77",
        )
    )

    assert result.status == "mapped"
    assert result.agent_mode == "model"
    assert result.model_id == "fake-seedpro"
    assert result.case is not None
    assert result.case.scoring_standard == "宽松标准"
    assert result.mappings["scoring_standard"].source_column == "F"


def test_schema_mapping_agent_repairs_model_output_with_validator_feedback() -> None:
    first = {
        "mappings": {
            "case_id": {"source_column": "A", "confidence": 0.98, "reason": "row id"},
            "prompt": {"source_column": "B", "confidence": 0.95, "reason": "prompt"},
            "golden_answer_json": {"source_column": "D", "confidence": 0.94, "reason": "reference answer"},
            "scoring_standard": {"source_column": "E", "confidence": 0.91, "reason": "rubric"},
        }
    }
    repaired = {
        "mappings": {
            "case_id": {"source_column": "A", "confidence": 0.98, "reason": "row id"},
            "prompt": {"source_column": "B", "confidence": 0.95, "reason": "prompt"},
            "predictions_json": {"source_column": "C", "confidence": 0.94, "reason": "observed output"},
            "expected_output_json": {"source_column": "D", "confidence": 0.94, "reason": "reference answer"},
            "scoring_standard": {"source_column": "E", "confidence": 0.91, "reason": "rubric"},
        }
    }
    agent = SpreadsheetSchemaMappingAgent(
        model_adapter=FakeModelAdapter(
            outputs=[json.dumps(first), json.dumps(repaired)],
            model_name="fake-seedpro",
        )
    )

    result = asyncio.run(
        agent.map_row_with_model(
            headers={
                "A": "id",
                "B": "prompt",
                "C": "actual output",
                "D": "reference",
                "E": "rubric",
            },
            values={
                "A": "CASE-88",
                "B": "Return JSON.",
                "C": '{"answer":"bad"}',
                "D": '{"answer":"good"}',
                "E": "answer must match",
            },
            sheet_row_id="8",
            target_label="CASE-88",
        )
    )

    assert result.status == "mapped"
    assert result.agent_mode == "model"
    assert result.validation_attempts == 2
    assert result.case is not None
    assert result.case.case_id == "CASE-88"


def test_schema_mapping_agent_does_not_fallback_to_rules_when_model_fails() -> None:
    agent = SpreadsheetSchemaMappingAgent(model_error="missing model credential")

    result = asyncio.run(
        agent.map_row_with_model(
            headers={"A": "id", "B": "prompt", "C": "predict", "D": "参考答案", "E": "评分标准"},
            values={
                "A": "CASE-89",
                "B": "Return JSON.",
                "C": '{"answer":"bad"}',
                "D": '{"answer":"good"}',
                "E": "answer must match",
            },
            sheet_row_id="9",
            target_label="CASE-89",
        )
    )

    assert result.status == "invalid"
    assert result.case is None
    assert result.agent_mode == "model"
    assert result.model_error == "missing model credential"


def test_schema_mapping_agent_selects_one_scoring_column_without_merging_user_data() -> None:
    result = SpreadsheetSchemaMappingAgent().map_row(
        headers={
            "A": "id",
            "B": "user prompt",
            "C": "predict",
            "D": "参考答案",
            "E": "评分标准（详细版）",
            "F": "评分标准（宽松版）",
        },
        values={
            "A": "JSZN-131",
            "B": "Segment the video and return JSON.",
            "C": '{"video_action_segments":[]}',
            "D": '{"video_action_segments":[{"subtask_label":"pick","start_s":0.1,"end_s":1.0}]}',
            "E": "详细标准：严格匹配动作、顺序和时间。",
            "F": "宽松标准：只检查动作顺序。",
        },
        sheet_row_id="2",
        target_label="JSZN-131",
    )

    assert result.status == "mapped"
    assert result.case is not None
    assert result.case.scoring_standard == "详细标准：严格匹配动作、顺序和时间。"
    assert "宽松标准" not in result.case.scoring_standard
    assert result.mappings["scoring_standard"].source_header == "评分标准（详细版）"
    assert any("scoring_standard 还有候选列未采用" in item for item in result.warnings)


def test_schema_mapping_agent_reports_missing_real_data_without_building_case() -> None:
    result = SpreadsheetSchemaMappingAgent().map_row(
        headers={
            "A": "样本编号",
            "B": "用户问题",
            "C": "标准答案",
        },
        values={
            "A": "CASE-404",
            "B": "Classify sentiment.",
            "C": '{"label":"positive"}',
        },
        sheet_row_id="3",
        target_label="CASE-404",
    )

    assert result.status == "missing_required"
    assert result.case is None
    assert set(result.missing_fields) >= {"predictions_json", "scoring_standard"}

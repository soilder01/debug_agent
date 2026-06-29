from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.recipes import recipe_for_task_type


def test_multimodal_fixture_set_covers_required_modalities() -> None:
    image_text_case = load_fixture_case("multimodal_image_text_alignment_001")
    single_image_case = load_fixture_case("single_image_detection_001")
    video_case = load_fixture_case("video_action_timestamp_001")
    text_schema_case = load_fixture_case("text_json_schema_001")

    assert image_text_case.task_type == "multimodal_detection"
    assert image_text_case.expected_output["conflicts"][0]["target_id"] == "multimodal:conflict:1"
    assert recipe_for_task_type(image_text_case.task_type).task_type == "multimodal_detection"

    assert single_image_case.task_type == "image_detection"
    assert single_image_case.expected_output["regions"][0]["target_id"] == "image:region:1"
    assert recipe_for_task_type(single_image_case.task_type).task_type == "image_detection"

    assert video_case.task_type == "video_detection"
    assert video_case.expected_output["temporal_segments"][0]["target_id"] == "video:segment:1"
    assert "check_timestamp" in video_case.scoring_standard
    assert recipe_for_task_type(video_case.task_type).task_type == "video_detection"

    assert text_schema_case.task_type == "classification"
    assert text_schema_case.expected_output["label"] == "unsafe"
    assert recipe_for_task_type(text_schema_case.task_type).task_type == "classification"


def test_round4_real_scenario_fixture_matrix_covers_five_categories() -> None:
    required_cases = {
        "video_time_boundary": load_fixture_case("video_action_timestamp_001"),
        "image_region_localization": load_fixture_case("single_image_detection_001"),
        "text_json_schema": load_fixture_case("text_json_schema_001"),
        "multimodal_alignment": load_fixture_case("multimodal_image_text_alignment_001"),
        "handwriting_ocr": load_fixture_case("handwrite233"),
    }

    assert set(required_cases) == {
        "video_time_boundary",
        "image_region_localization",
        "text_json_schema",
        "multimodal_alignment",
        "handwriting_ocr",
    }
    assert {case.task_type for case in required_cases.values()} >= {
        "video_detection",
        "image_detection",
        "classification",
        "multimodal_detection",
        "handwriting_ocr",
    }

import json
from tempfile import TemporaryDirectory
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from PIL import Image

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan, ExperimentStep, plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.adapters import ModelResponse
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe


@pytest.mark.asyncio
async def test_run_experiments_collects_judged_evidence() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.case_id == "handwrite233"
    assert result.total_trials == 6
    assert result.success_count == 0
    assert result.evidence[0].step_name == "baseline_replay"
    assert result.evidence[0].model_name == "fake"
    assert result.evidence[0].model_provider == "fake"
    assert result.evidence[0].model_id == "fake"
    assert result.evidence[0].request_summary == {
        "agent_role": "model_runner",
        "prompt_length": len(case.prompt),
        "has_image": bool(case.image_uri),
        "image_uri_scheme": urlparse(case.image_uri).scheme,
        "scoring_standard_present": True,
    }
    assert result.evidence[0].latency_ms >= 0
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.scoring_standard == case.scoring_standard
    assert result.evidence[0].judge.affected_box_ids
    assert "student_answer_mismatch" in result.evidence[0].judge.reasons[0]


@pytest.mark.asyncio
async def test_run_experiments_keeps_malformed_model_output_as_evidence() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[
            ExperimentStep(
                name="malformed_output",
                description="Keep malformed output as evidence.",
                trials=1,
            )
        ],
    )
    adapter = FakeModelAdapter(outputs=["not-json"])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.total_trials == 1
    assert result.success_count == 0
    assert result.evidence[0].raw_output == "not-json"
    assert result.evidence[0].response_parse_error
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["response_parse_error"]


class TimeoutModelAdapter:
    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        del prompt, image_uri
        raise TimeoutError("model request timed out")


class PromptRecordingModelAdapter:
    def __init__(self, raw_output: str) -> None:
        self.raw_output = raw_output
        self.prompts: list[str] = []

    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        del image_uri
        self.prompts.append(prompt)
        return ModelResponse(model_name="recording", trial=0, raw_output=self.raw_output)


@pytest.mark.asyncio
async def test_run_experiments_keeps_model_call_error_as_evidence() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[
            ExperimentStep(
                name="timeout_call",
                description="Keep model timeout as evidence.",
                trials=1,
            )
        ],
    )

    result = await run_experiments(case=case, plan=plan, adapter=TimeoutModelAdapter())

    assert result.total_trials == 1
    assert result.success_count == 0
    assert result.evidence[0].raw_output == ""
    assert result.evidence[0].model_call_error_type == "TimeoutError"
    assert result.evidence[0].model_call_error_message == "model request timed out"
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["model_call_error"]


@pytest.mark.asyncio
async def test_run_experiments_adds_localized_image_artifacts_for_affected_boxes() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "case-localized",
            "image_uri": "file:///tmp/case-localized.png",
            "prompt": "识别作答区域。",
            "golden_answer": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":7,\"student_answer\":\"低温烘干\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "box_regions": [
                {
                    "box_id": 7,
                    "x": 12,
                    "y": 34,
                    "width": 56,
                    "height": 78,
                    "unit": "pixel",
                    "label": "box-7",
                }
            ],
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[
            ExperimentStep(
                name="localized_observation_request",
                description="Ask the model to inspect the affected answer box.",
                trials=1,
            )
        ],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    artifact = result.evidence[0].image_artifacts[0]
    assert artifact.artifact_id == "case-localized:box-7:localized-candidate"
    assert artifact.kind == "affected_box_candidate"
    assert artifact.source_image_uri == "file:///tmp/case-localized.png"
    assert artifact.derived_image_uri == ""
    assert artifact.region is not None
    assert artifact.region.x == 12
    assert artifact.region.y == 34
    assert artifact.region.width == 56
    assert artifact.region.height == 78
    assert artifact.region.label == "box-7"
    generic_artifact = result.evidence[0].artifacts[0]
    assert generic_artifact.artifact_id == "case-localized:box-7:localized-candidate"
    assert generic_artifact.kind == "affected_box_candidate"
    assert generic_artifact.artifact_type == "image"
    assert generic_artifact.source_uri == "file:///tmp/case-localized.png"
    assert generic_artifact.derived_uri == ""
    assert generic_artifact.preview_url == ""
    assert generic_artifact.region is not None
    assert generic_artifact.region.label == "box-7"
    assert generic_artifact.metadata == {"target_id": "box:7", "legacy_kind": "affected_box_candidate"}


@pytest.mark.asyncio
async def test_run_experiments_adds_generic_input_and_output_artifacts() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    artifact_kinds = [artifact.kind for artifact in result.evidence[0].artifacts]
    assert "input_snapshot" in artifact_kinds
    assert "structured_output" in artifact_kinds


@pytest.mark.asyncio
async def test_run_experiments_materializes_localized_crop_artifacts() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        source_image_path = temp_path / "case-localized.png"
        artifact_dir = temp_path / "artifacts"
        result = await _run_localized_crop_case(source_image_path=source_image_path, artifact_dir=artifact_dir)

        artifact = result.evidence[0].image_artifacts[0]
        assert artifact.derived_image_uri
        assert artifact.preview_image_url == "/api/artifacts/images/case-localized-crop_box-7_localized-candidate.png"
        crop_path = _path_from_file_uri(artifact.derived_image_uri)
        assert crop_path.exists()
        with Image.open(crop_path) as crop:
            assert crop.size == (56, 20)


async def _run_localized_crop_case(source_image_path: Path, artifact_dir: Path):
    Image.new("RGB", (100, 100), color="white").save(source_image_path)
    case = DebugCase.model_validate(
        {
            "case_id": "case-localized-crop",
            "image_uri": source_image_path.as_uri(),
            "prompt": "识别作答区域。",
            "golden_answer": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":7,\"student_answer\":\"低温烘干\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "box_regions": [
                {
                    "box_id": 7,
                    "x": 12,
                    "y": 34,
                    "width": 56,
                    "height": 20,
                    "unit": "pixel",
                    "label": "box-7",
                }
            ],
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[
            ExperimentStep(
                name="localized_observation_request",
                description="Ask the model to inspect the affected answer box.",
                trials=1,
            )
        ],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    return await run_experiments(
        case=case,
        plan=plan,
        adapter=adapter,
        image_artifact_dir=artifact_dir,
    )


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text)


@pytest.mark.asyncio
async def test_run_experiments_sends_localized_prompt_with_affected_region_context() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "case-localized-prompt",
            "image_uri": "file:///tmp/case-localized-prompt.png",
            "prompt": "仅识别题目对应作答区域内的学生全部作答内容。",
            "golden_answer": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":7,\"student_answer\":\"低温烘干\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "box_regions": [
                {
                    "box_id": 7,
                    "x": 12,
                    "y": 34,
                    "width": 56,
                    "height": 78,
                    "unit": "pixel",
                    "label": "box-7",
                }
            ],
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[
            ExperimentStep(
                name="localized_observation_request",
                description="Ask the model to inspect the affected answer box.",
                trials=1,
            )
        ],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert len(adapter.prompts) == 1
    assert "仅识别题目对应作答区域内的学生全部作答内容。" in adapter.prompts[0]
    assert "localized_observation_request" in adapter.prompts[0]
    assert "box 7" in adapter.prompts[0]
    assert "x=12, y=34, width=56, height=78, unit=pixel, label=box-7" in adapter.prompts[0]


@pytest.mark.asyncio
async def test_run_experiments_builds_prompts_through_task_recipe(monkeypatch) -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    def recording_prompt(self, *, case: DebugCase, step_name: str) -> str:
        del self
        return f"recipe prompt for {case.case_id}:{step_name}"

    monkeypatch.setattr(HandwritingOcrRecipe, "build_step_prompt", recording_prompt)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert adapter.prompts == ["recipe prompt for handwrite233:baseline_replay"]


@pytest.mark.asyncio
async def test_run_experiments_uses_classification_recipe_prompt() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-runner",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"label\":\"negative\",\"confidence\":0.61}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="label_schema_check", description="Check labels.", trials=1)],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert len(adapter.prompts) == 1
    assert "label_schema_check" in adapter.prompts[0]
    assert "expected label" in adapter.prompts[0]
    assert "affected answer region" not in adapter.prompts[0]


@pytest.mark.asyncio
async def test_run_experiments_judges_classification_output_natively() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-native-runner",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"label\":\"negative\",\"confidence\":0.61}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.evidence[0].response_parse_error == ""
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["label:classification label_mismatch"]
    assert result.evidence[0].judge.deltas == [
        {
            "target_id": "label:classification",
            "expected": "positive",
            "actual": "negative",
            "reason": "label_mismatch",
            "metadata": {"field": "label", "confidence": 0.61},
        }
    ]


@pytest.mark.asyncio
async def test_run_experiments_prefers_classification_expected_output_over_legacy_answer() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-expected-output",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-negative"}]},
            "expected_output": {"label": "positive"},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"label\":\"positive\",\"confidence\":0.9}", "score": 1}],
            "avg_score": 1.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.evidence[0].response_parse_error == ""
    assert result.evidence[0].judge.score == 1
    assert result.evidence[0].judge.reasons == []


@pytest.mark.asyncio
async def test_run_experiments_judges_image_detection_output_natively() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "image-detection-native-runner",
            "task_type": "image_detection",
            "image_uri": "file:///tmp/image-detection.png",
            "prompt": "Detect the main animal and return region JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-cat"}]},
            "expected_output": {
                "regions": [
                    {
                        "target_id": "image:region:1",
                        "x": 10,
                        "y": 20,
                        "width": 30,
                        "height": 40,
                        "label": "cat",
                    }
                ]
            },
            "scoring_standard": "region target ids and labels must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": (
                        "{\"regions\":[{\"target_id\":\"image:region:1\",\"x\":10,\"y\":20,"
                        "\"width\":30,\"height\":40,\"label\":\"dog\",\"confidence\":0.57}]}"
                    ),
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.evidence[0].response_parse_error == ""
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["image:region:1 region_label_mismatch"]
    assert result.evidence[0].judge.affected_box_ids == []
    assert result.evidence[0].judge.deltas == [
        {
            "target_id": "image:region:1",
            "expected": "cat",
            "actual": "dog",
            "reason": "region_label_mismatch",
            "metadata": {"field": "label", "confidence": 0.57},
        }
    ]


@pytest.mark.asyncio
async def test_run_experiments_uses_image_detection_recipe_prompt() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "image-detection-prompt",
            "task_type": "image_detection",
            "image_uri": "file:///tmp/image-detection-prompt.png",
            "prompt": "Detect objects and return region JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-cat"}]},
            "expected_output": {
                "regions": [
                    {
                        "target_id": "image:region:1",
                        "x": 10,
                        "y": 20,
                        "width": 30,
                        "height": 40,
                        "label": "cat",
                    }
                ]
            },
            "scoring_standard": "region target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"regions\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="localization_prompt_check", description="Check localization.", trials=1)],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert len(adapter.prompts) == 1
    assert "localization_prompt_check" in adapter.prompts[0]
    assert "image:region:1" in adapter.prompts[0]
    assert "region target ids and labels must match." in adapter.prompts[0]
    assert "affected answer region" not in adapter.prompts[0]


@pytest.mark.asyncio
async def test_run_experiments_judges_video_detection_output_natively() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "video-detection-native-runner",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/video-detection.mp4",
            "prompt": "Detect the event and return temporal segment JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-event"}]},
            "expected_output": {
                "temporal_segments": [
                    {
                        "target_id": "video:segment:1",
                        "start_ms": 1000,
                        "end_ms": 2500,
                        "label": "person_enters",
                    }
                ]
            },
            "scoring_standard": "temporal segment target ids and labels must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": (
                        "{\"temporal_segments\":[{\"target_id\":\"video:segment:1\",\"start_ms\":1000,"
                        "\"end_ms\":2500,\"label\":\"person_leaves\",\"confidence\":0.62}]}"
                    ),
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.evidence[0].response_parse_error == ""
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["video:segment:1 segment_label_mismatch"]
    assert result.evidence[0].judge.affected_box_ids == []
    assert result.evidence[0].judge.deltas == [
        {
            "target_id": "video:segment:1",
            "expected": "person_enters",
            "actual": "person_leaves",
            "reason": "segment_label_mismatch",
            "metadata": {"field": "label", "confidence": 0.62},
        }
    ]


@pytest.mark.asyncio
async def test_run_experiments_uses_video_detection_recipe_prompt() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "video-detection-prompt",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/video-detection-prompt.mp4",
            "prompt": "Detect events and return temporal segment JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-event"}]},
            "expected_output": {
                "temporal_segments": [
                    {
                        "target_id": "video:segment:1",
                        "start_ms": 1000,
                        "end_ms": 2500,
                        "label": "person_enters",
                    }
                ]
            },
            "scoring_standard": "temporal segment target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"temporal_segments\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="temporal_grounding_check", description="Check grounding.", trials=1)],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert len(adapter.prompts) == 1
    assert "temporal_grounding_check" in adapter.prompts[0]
    assert "video:segment:1" in adapter.prompts[0]
    assert "temporal segment target ids and labels must match." in adapter.prompts[0]
    assert "affected answer region" not in adapter.prompts[0]


@pytest.mark.asyncio
async def test_run_experiments_judges_multimodal_detection_output_natively() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-detection-native-runner",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal-input.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-conflict"}]},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches the visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": (
                        "{\"conflicts\":[{\"target_id\":\"multimodal:conflict:1\","
                        "\"conflict_type\":\"visual_text_conflict\",\"modalities\":[\"image\",\"text\"],"
                        "\"expected\":\"caption matches the visual subject\","
                        "\"actual\":\"image shows dog while caption says cat\",\"confidence\":0.76}]}"
                    ),
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="baseline_replay", description="Replay baseline.", trials=1)],
    )
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.evidence[0].response_parse_error == ""
    assert result.evidence[0].judge.score == 0
    assert result.evidence[0].judge.reasons == ["multimodal:conflict:1 conflict_actual_mismatch"]
    assert result.evidence[0].judge.affected_box_ids == []
    assert result.evidence[0].judge.deltas == [
        {
            "target_id": "multimodal:conflict:1",
            "expected": "image and caption both describe a cat",
            "actual": "image shows dog while caption says cat",
            "reason": "conflict_actual_mismatch",
            "metadata": {
                "field": "actual",
                "conflict_type": "visual_text_conflict",
                "modalities": ["image", "text"],
                "confidence": 0.76,
            },
        }
    ]


@pytest.mark.asyncio
async def test_run_experiments_uses_multimodal_detection_recipe_prompt() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-detection-prompt",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal-input.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-conflict"}]},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches the visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = ExperimentPlan(
        case_id=case.case_id,
        max_model_calls=1,
        steps=[ExperimentStep(name="modality_ablation_check", description="Check modality ablation.", trials=1)],
    )
    adapter = PromptRecordingModelAdapter(raw_output=case.predictions[0].raw_output)

    await run_experiments(case=case, plan=plan, adapter=adapter)

    assert len(adapter.prompts) == 1
    assert "modality_ablation_check" in adapter.prompts[0]
    assert "multimodal:conflict:1" in adapter.prompts[0]
    assert "visual_text_conflict" in adapter.prompts[0]
    assert "cross-modal claims must agree." in adapter.prompts[0]
    assert "answer-box assumptions" not in adapter.prompts[0]

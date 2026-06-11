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
        "prompt_length": len(case.prompt),
        "has_image": bool(case.image_uri),
        "image_uri_scheme": urlparse(case.image_uri).scheme,
    }
    assert result.evidence[0].latency_ms >= 0
    assert result.evidence[0].judge.score == 0
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

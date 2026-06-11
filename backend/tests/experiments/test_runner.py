import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan, ExperimentStep, plan_experiments
from debug_agent.experiments.runner import run_experiments
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

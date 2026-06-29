import pytest

from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure.strategy_agents import (
    hypotheses_from_strategy_payload,
    run_hypothesis_strategy_agent,
)
from debug_agent.models.config import AgentModelConfig, AgentModelSelection
from debug_agent.reports.generator import DebugReport, ExperimentSummary, ObservedFailure, RootCause


@pytest.mark.asyncio
async def test_hypothesis_strategy_agent_normalizes_visible_json_output() -> None:
    case = _case_with_strategy_agent_output(
        """
        {
          "hypotheses": [
            {
              "hypothesis_id": "h-unsafe",
              "category": "prompt_constraint",
              "claim": "Prompt misses required right-arm and both-arm details.",
              "supporting_evidence_ids": [],
              "missing_evidence": [],
              "confidence_before_probe": "high",
              "status": "supported"
            }
          ]
        }
        """
    )
    config = AgentModelConfig(
        roles={
            "hypothesis_strategist": AgentModelSelection(
                provider="fake",
                model_id="seedpro",
                thinking="enabled",
            )
        }
    )

    result = await run_hypothesis_strategy_agent(
        case=case,
        report=_report(),
        config=config,
    )

    assert result.error_message == ""
    assert len(result.hypotheses) == 1
    hypothesis = result.hypotheses[0]
    assert hypothesis.hypothesis_id == "h-unsafe"
    assert hypothesis.status == "candidate"
    assert hypothesis.confidence_before_probe == "low"
    assert result.agent_trace.agent_role == "hypothesis_strategist"
    assert result.agent_trace.raw_cot_policy == "visible_output_summary_only"
    assert "h-unsafe" in result.agent_trace.output_excerpt


@pytest.mark.asyncio
async def test_hypothesis_strategy_agent_falls_back_when_role_is_not_configured() -> None:
    result = await run_hypothesis_strategy_agent(
        case=_case_with_strategy_agent_output("{}"),
        report=_report(),
        config=AgentModelConfig(roles={}),
    )

    assert result.hypotheses == []
    assert result.error_message == "model not configured"
    assert result.agent_trace.agent_role == "hypothesis_strategist"
    assert "model not configured" in result.agent_trace.reasoning_summary


def test_hypotheses_from_strategy_payload_drops_invalid_categories() -> None:
    hypotheses = hypotheses_from_strategy_payload(
        {
            "hypotheses": [
                {
                    "hypothesis_id": "h-valid",
                    "category": "model_stability",
                    "claim": "Locked reruns may be unstable.",
                },
                {
                    "hypothesis_id": "h-invalid",
                    "category": "freeform_guess",
                    "claim": "Unsupported category should be ignored.",
                },
            ]
        }
    )

    assert [item.hypothesis_id for item in hypotheses] == ["h-valid"]


def _case_with_strategy_agent_output(raw_output: str) -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "case-hypothesis-strategy",
            "task_type": "generic_video_json",
            "image_uri": "https://example.com/video.mp4",
            "prompt": "Describe the video as JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {"tasks": []},
            "scoring_standard": "right arm and both-arm coordination are required.",
            "predictions": [{"trial": 0, "raw_output": raw_output, "score": 0}],
            "avg_score": 0.0,
        }
    )


def _report() -> DebugReport:
    return DebugReport(
        job_id="job-hypothesis-strategy",
        case_id="case-hypothesis-strategy",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="output_mismatch",
            summary="The model omitted right-arm details.",
            affected_box_ids=[],
        ),
        planned_experiments=["baseline_replay"],
        experiment_summary=ExperimentSummary(
            total_trials=1,
            success_count=0,
            failed_trial_count=1,
            success_rate=0,
            evidence_ids=["e-baseline"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label="output_mismatch",
            confidence="medium",
            evidence_summary="baseline replay missed required details.",
        ),
        suggested_sheet_fields={"错误原因": "候选假设待验证"},
    )

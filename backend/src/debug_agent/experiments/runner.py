from time import perf_counter
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from debug_agent.cases.comparator import parse_prediction_answer
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.judging.runner import JudgeResult, judge_answer
from debug_agent.models.adapters import ModelAdapter


class ImageRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int
    unit: str = "pixel"
    label: str = ""


class ImageArtifact(BaseModel):
    artifact_id: str
    kind: str
    source_image_uri: str
    region: ImageRegion | None = None
    derived_image_uri: str = ""


class ExperimentEvidence(BaseModel):
    evidence_id: str
    step_name: str
    trial: int
    model_name: str = ""
    model_provider: str = ""
    model_id: str = ""
    request_summary: dict[str, object] = {}
    latency_ms: int = 0
    response_parse_error: str = ""
    model_call_error_type: str = ""
    model_call_error_message: str = ""
    image_artifacts: list[ImageArtifact] = Field(default_factory=list)
    raw_output: str
    judge: JudgeResult


class ExperimentRunResult(BaseModel):
    case_id: str
    total_trials: int
    success_count: int
    evidence: list[ExperimentEvidence]


async def run_experiments(
    case: DebugCase,
    plan: ExperimentPlan,
    adapter: ModelAdapter,
) -> ExperimentRunResult:
    evidence: list[ExperimentEvidence] = []
    success_count = 0
    for step in plan.steps:
        for trial_index in range(step.trials):
            started_at = perf_counter()
            model_call_error_type = ""
            model_call_error_message = ""
            try:
                response = await adapter.generate(prompt=case.prompt, image_uri=case.image_uri)
            except Exception as exc:
                latency_ms = int((perf_counter() - started_at) * 1000)
                model_call_error_type = type(exc).__name__
                model_call_error_message = str(exc)
                judge = JudgeResult(score=0, reasons=["model_call_error"])
                evidence.append(
                    ExperimentEvidence(
                        evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                        step_name=step.name,
                        trial=trial_index,
                        request_summary=_build_request_summary(prompt=case.prompt, image_uri=case.image_uri),
                        latency_ms=latency_ms,
                        model_call_error_type=model_call_error_type,
                        model_call_error_message=model_call_error_message,
                        raw_output="",
                        judge=judge,
                    )
                )
                continue
            latency_ms = int((perf_counter() - started_at) * 1000)
            response_parse_error = ""
            try:
                predicted = parse_prediction_answer(response.raw_output)
                judge = judge_answer(case.golden_answer, predicted)
            except Exception as exc:
                response_parse_error = str(exc)
                judge = JudgeResult(score=0, reasons=["response_parse_error"])
            success_count += judge.score
            evidence.append(
                ExperimentEvidence(
                    evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                    step_name=step.name,
                    trial=trial_index,
                    model_name=response.model_name,
                    model_provider=response.model_provider,
                    model_id=response.model_id,
                    request_summary=_build_request_summary(prompt=case.prompt, image_uri=case.image_uri),
                    latency_ms=latency_ms,
                    response_parse_error=response_parse_error,
                    model_call_error_type=model_call_error_type,
                    model_call_error_message=model_call_error_message,
                    raw_output=response.raw_output,
                    judge=judge,
                )
            )
    return ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=success_count,
        evidence=evidence,
    )


def _build_request_summary(prompt: str, image_uri: str) -> dict[str, object]:
    parsed_uri = urlparse(image_uri)
    return {
        "prompt_length": len(prompt),
        "has_image": bool(image_uri),
        "image_uri_scheme": parsed_uri.scheme,
    }

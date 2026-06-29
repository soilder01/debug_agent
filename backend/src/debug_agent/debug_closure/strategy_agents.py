from __future__ import annotations

import hashlib
import json
from time import perf_counter

from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure.hypotheses import DebugHypothesis, normalize_hypotheses
from debug_agent.models.config import AgentModelConfig, build_adapter_for_selection
from debug_agent.reports.generator import AgentTrace, DebugReport


class HypothesisStrategyAgentResult(BaseModel):
    hypotheses: list[DebugHypothesis] = Field(default_factory=list)
    error_message: str = ""
    agent_trace: AgentTrace


async def run_hypothesis_strategy_agent(
    *,
    case: DebugCase,
    report: DebugReport,
    config: AgentModelConfig,
) -> HypothesisStrategyAgentResult:
    prompt = hypothesis_strategy_prompt(case=case, report=report)
    selection = config.roles.get("hypothesis_strategist")
    if selection is None:
        error_message = "model not configured"
        return HypothesisStrategyAgentResult(
            hypotheses=[],
            error_message=error_message,
            agent_trace=_agent_trace(
                case=case,
                prompt=prompt,
                payload={},
                raw_output="",
                status="fallback",
                model_id="",
                latency_ms=0,
                error_message=error_message,
            ),
        )
    started_at = perf_counter()
    try:
        adapter = build_adapter_for_selection(case=case, selection=selection)
        response = await adapter.generate(prompt=prompt, image_uri="")
        latency_ms = int((perf_counter() - started_at) * 1000)
        payload = _extract_json_object(response.raw_output)
        hypotheses = hypotheses_from_strategy_payload(payload)
        return HypothesisStrategyAgentResult(
            hypotheses=hypotheses,
            agent_trace=_agent_trace(
                case=case,
                prompt=prompt,
                payload=payload,
                raw_output=response.raw_output,
                status="completed",
                model_id=response.model_id or selection.model_id,
                latency_ms=latency_ms,
                error_message="",
            ),
        )
    except Exception as exc:
        return HypothesisStrategyAgentResult(
            hypotheses=[],
            error_message=str(exc),
            agent_trace=_agent_trace(
                case=case,
                prompt=prompt,
                payload={},
                raw_output="",
                status="fallback",
                model_id=selection.model_id,
                latency_ms=int((perf_counter() - started_at) * 1000),
                error_message=str(exc),
            ),
        )


def hypotheses_from_strategy_payload(payload: dict[str, object]) -> list[DebugHypothesis]:
    value = payload.get("hypotheses")
    if not isinstance(value, list):
        return []
    hypotheses: list[DebugHypothesis] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            hypotheses.append(DebugHypothesis.model_validate(item))
        except Exception:
            continue
    return normalize_hypotheses(hypotheses)


def hypothesis_strategy_prompt(*, case: DebugCase, report: DebugReport) -> str:
    evidence_ids = report.experiment_summary.evidence_ids if report.experiment_summary else []
    return "\n".join(
        [
            "You are Debug Agent's hypothesis_strategist.",
            "Return one JSON object only. Do not return Markdown.",
            "You may propose candidate root-cause hypotheses only.",
            "Do not execute model reruns, do not inspect media, and do not mark any hypothesis supported.",
            "Allowed categories: prompt_constraint, scoring_strictness, golden_answer_ambiguity, model_stability, input_evidence, schema_constraint, judge_disagreement, media_resolution.",
            'Schema: {"hypotheses":[{"hypothesis_id":"...","category":"prompt_constraint","claim":"...","supporting_evidence_ids":["..."],"missing_evidence":["..."],"confidence_before_probe":"low","status":"candidate"}]}',
            f"case_id={case.case_id}",
            f"task_type={case.task_type}",
            f"case_prompt={_clip(case.prompt, 1200)}",
            f"scoring_standard={_clip(case.scoring_standard, 1200)}",
            f"observed_failure={report.observed_failure.model_dump_json()}",
            f"root_cause={report.root_cause.model_dump_json()}",
            f"evidence_ids={json.dumps(evidence_ids, ensure_ascii=False)}",
            f"debug_strategy={json.dumps(report.debug_strategy, ensure_ascii=False)}",
            f"judge_comparison_notes={json.dumps(report.judge_comparison_notes, ensure_ascii=False)}",
        ]
    )


def _agent_trace(
    *,
    case: DebugCase,
    prompt: str,
    payload: dict[str, object],
    raw_output: str,
    status: str,
    model_id: str,
    latency_ms: int,
    error_message: str,
) -> AgentTrace:
    return AgentTrace(
        agent_role="hypothesis_strategist",
        input_summary={
            "case_id": case.case_id,
            "task_type": case.task_type,
            "prompt_character_count": len(prompt),
            "model_id": model_id,
            "status": status,
        },
        input_excerpt=_clip(prompt, 4000),
        input_sha256=_sha256_text(prompt),
        output_summary={
            "status": status,
            "json_keys": sorted(str(key) for key in payload.keys()),
            "raw_output_character_count": len(raw_output),
            "latency_ms": latency_ms,
            "error_message": error_message,
        },
        output_excerpt=_clip(raw_output, 4000),
        reasoning_summary=_reasoning_summary(payload=payload, error_message=error_message),
        raw_cot_policy="visible_output_summary_only",
    )


def _reasoning_summary(*, payload: dict[str, object], error_message: str) -> str:
    if error_message:
        return f"Agent fallback: {error_message}"
    hypotheses = payload.get("hypotheses")
    if not isinstance(hypotheses, list):
        return "Agent returned no candidate hypotheses."
    claims = [
        str(item.get("claim", "")).strip()
        for item in hypotheses
        if isinstance(item, dict) and str(item.get("claim", "")).strip()
    ]
    if claims:
        return "; ".join(claims[:3])
    return "Agent returned structured hypothesis JSON; hidden CoT was not collected."


def _extract_json_object(raw_output: str) -> dict[str, object]:
    stripped = raw_output.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("hypothesis strategy agent output did not contain a JSON object")
    decoded = json.loads(stripped[start : end + 1])
    if not isinstance(decoded, dict):
        raise ValueError("hypothesis strategy agent output must be a JSON object")
    return decoded


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


def _clip(value: str, limit: int) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."

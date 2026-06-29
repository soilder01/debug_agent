import hashlib
import json
from time import perf_counter
from typing import TypedDict

from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentRunResult
from debug_agent.models.config import AgentModelConfig, AgentModelRole, build_adapter_for_selection
from debug_agent.reports.generator import AgentTrace, DebugReport


class MetaAgentTelemetry(BaseModel):
    agent_role: str
    status: str
    model_provider: str = ""
    model_id: str = ""
    model_name: str = ""
    mode: str = ""
    thinking: str = ""
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_units: float = 0.0
    error_message: str = ""


class MetaAgentEnrichment(BaseModel):
    status: str = "fallback"
    root_cause_summary: str = ""
    strategy_updates: list[dict[str, str]] = Field(default_factory=list)
    judge_comparison_notes: list[dict[str, str]] = Field(default_factory=list)
    recommended_actions: list[dict[str, str]] = Field(default_factory=list)
    confidence_reasons: list[dict[str, str]] = Field(default_factory=list)
    telemetry: list[MetaAgentTelemetry] = Field(default_factory=list)
    agent_traces: list[AgentTrace] = Field(default_factory=list)


class _AgentRunResult(TypedDict):
    payload: dict[str, object]
    telemetry: MetaAgentTelemetry
    agent_trace: AgentTrace


async def run_report_meta_agents(
    *,
    case: DebugCase,
    report: DebugReport,
    run_result: ExperimentRunResult,
    config: AgentModelConfig,
) -> MetaAgentEnrichment:
    enrichment = MetaAgentEnrichment()
    root_cause_result = await _run_json_agent(
        role_id="report_root_cause",
        case=case,
        config=config,
        prompt=_root_cause_prompt(case=case, report=report, run_result=run_result),
    )
    enrichment.telemetry.append(root_cause_result["telemetry"])
    enrichment.agent_traces.append(root_cause_result["agent_trace"])
    if root_cause_result["payload"]:
        payload = root_cause_result["payload"]
        summary = payload.get("root_cause_summary")
        if isinstance(summary, str):
            enrichment.root_cause_summary = summary
        actions = payload.get("recommended_actions")
        if isinstance(actions, list):
            enrichment.recommended_actions = [
                _string_dict(item) for item in actions if isinstance(item, dict)
            ]
        confidence = payload.get("confidence_reasons")
        if isinstance(confidence, list):
            enrichment.confidence_reasons = [
                _string_dict(item) for item in confidence if isinstance(item, dict)
            ]

    planner_result = await _run_json_agent(
        role_id="experiment_planner",
        case=case,
        config=config,
        prompt=_planner_prompt(case=case, report=report, run_result=run_result),
    )
    enrichment.telemetry.append(planner_result["telemetry"])
    enrichment.agent_traces.append(planner_result["agent_trace"])
    if planner_result["payload"]:
        strategy = planner_result["payload"].get("strategy_updates")
        if isinstance(strategy, list):
            enrichment.strategy_updates = [
                _string_dict(item) for item in strategy if isinstance(item, dict)
            ]

    judge_result = await _run_json_agent(
        role_id="judge_comparator",
        case=case,
        config=config,
        prompt=_judge_comparator_prompt(case=case, report=report, run_result=run_result),
    )
    enrichment.telemetry.append(judge_result["telemetry"])
    enrichment.agent_traces.append(judge_result["agent_trace"])
    if judge_result["payload"]:
        notes = judge_result["payload"].get("judge_comparison_notes")
        if isinstance(notes, list):
            enrichment.judge_comparison_notes = [
                _string_dict(item) for item in notes if isinstance(item, dict)
            ]

    if any(item.status == "completed" for item in enrichment.telemetry):
        enrichment.status = "completed"
    return enrichment


async def _run_json_agent(
    *,
    role_id: AgentModelRole,
    case: DebugCase,
    config: AgentModelConfig,
    prompt: str,
) -> _AgentRunResult:
    selection = config.roles.get(role_id)
    if selection is None:
        telemetry = MetaAgentTelemetry(
            agent_role=role_id,
            status="fallback",
            error_message="model not configured",
        )
        return {
            "payload": {},
            "telemetry": telemetry,
            "agent_trace": _agent_trace(
                role_id=role_id,
                case=case,
                prompt=prompt,
                telemetry=telemetry,
                payload={},
                raw_output="",
            ),
        }
    started_at = perf_counter()
    telemetry = MetaAgentTelemetry(
        agent_role=role_id,
        status="running",
        model_provider=selection.provider,
        model_id=selection.model_id,
        mode=selection.mode,
        thinking=selection.thinking,
        temperature=selection.temperature,
        top_p=selection.top_p,
        max_tokens=selection.max_tokens,
    )
    try:
        adapter = build_adapter_for_selection(case=case, selection=selection)
        response = await adapter.generate(prompt=prompt, image_uri="")
        telemetry.status = "completed"
        telemetry.model_provider = response.model_provider or selection.provider
        telemetry.model_id = response.model_id or selection.model_id
        telemetry.model_name = response.model_name
        telemetry.latency_ms = int((perf_counter() - started_at) * 1000)
        telemetry.prompt_tokens = int(response.usage.get("prompt_tokens", 0))
        telemetry.completion_tokens = int(response.usage.get("completion_tokens", 0))
        telemetry.total_tokens = int(response.usage.get("total_tokens", 0))
        telemetry.estimated_cost_units = _estimated_cost_units(response.usage)
        try:
            payload = _extract_json_object(response.raw_output)
        except Exception as exc:
            telemetry.status = "fallback"
            telemetry.error_message = str(exc)
            return {
                "payload": {},
                "telemetry": telemetry,
                "agent_trace": _agent_trace(
                    role_id=role_id,
                    case=case,
                    prompt=prompt,
                    telemetry=telemetry,
                    payload={},
                    raw_output=response.raw_output,
                ),
            }
        return {
            "payload": payload,
            "telemetry": telemetry,
            "agent_trace": _agent_trace(
                role_id=role_id,
                case=case,
                prompt=prompt,
                telemetry=telemetry,
                payload=payload,
                raw_output=response.raw_output,
            ),
        }
    except Exception as exc:
        telemetry.status = "fallback"
        telemetry.error_message = str(exc)
        telemetry.latency_ms = int((perf_counter() - started_at) * 1000)
        return {
            "payload": {},
            "telemetry": telemetry,
            "agent_trace": _agent_trace(
                role_id=role_id,
                case=case,
                prompt=prompt,
                telemetry=telemetry,
                payload={},
                raw_output="",
            ),
        }


def _root_cause_prompt(
    *, case: DebugCase, report: DebugReport, run_result: ExperimentRunResult
) -> str:
    return (
        "你是 Debug Agent 的 Report Root Cause Agent。基于规则报告和 evidence 摘要，"
        "只输出 JSON object，不要输出 Markdown。字段："
        "root_cause_summary:string, recommended_actions:array, confidence_reasons:array。\n"
        f"case_id={case.case_id}\n"
        f"task_type={case.task_type}\n"
        f"rule_root_cause={report.root_cause.model_dump_json()}\n"
        f"observed_failure={report.observed_failure.model_dump_json()}\n"
        f"success_count={run_result.success_count}/{run_result.total_trials}\n"
        f"step_summaries={json.dumps(report.experiment_summary.step_summaries if report.experiment_summary else [], ensure_ascii=False)}\n"
    )


def _planner_prompt(
    *, case: DebugCase, report: DebugReport, run_result: ExperimentRunResult
) -> str:
    return (
        "你是 Debug Agent 的 Experiment Planner Agent。基于 evidence 和当前规则策略，"
        "提出下一步深挖策略。只输出 JSON object，不要输出 Markdown。字段："
        "strategy_updates:array，每项包含 stage, objective, planned_probe, stop_condition, escalation。\n"
        f"case_id={case.case_id}\n"
        f"task_type={case.task_type}\n"
        f"root_cause={report.root_cause.model_dump_json()}\n"
        f"existing_strategy={json.dumps(report.debug_strategy, ensure_ascii=False)}\n"
        f"success_count={run_result.success_count}/{run_result.total_trials}\n"
    )


def _judge_comparator_prompt(
    *, case: DebugCase, report: DebugReport, run_result: ExperimentRunResult
) -> str:
    return (
        "你是 Debug Agent 的 Judge Comparator Agent。你不能覆盖 deterministic judge score，"
        "只能基于 evidence delta 生成辅助比较备注。只输出 JSON object，不要输出 Markdown。字段："
        "judge_comparison_notes:array，每项包含 evidence_id, target_id, deterministic_reason, llm_note, risk。\n"
        f"case_id={case.case_id}\n"
        f"task_type={case.task_type}\n"
        f"root_cause={report.root_cause.model_dump_json()}\n"
        f"evidence={json.dumps(_judge_prompt_evidence(run_result), ensure_ascii=False)}\n"
    )


def _judge_prompt_evidence(run_result: ExperimentRunResult) -> list[dict[str, object]]:
    return [
        {
            "evidence_id": item.evidence_id,
            "step_name": item.step_name,
            "judge_score": item.judge.score,
            "judge_reasons": item.judge.reasons,
            "deltas": item.judge.deltas,
            "parse_error": item.response_parse_error,
            "model_call_error": item.model_call_error_type,
        }
        for item in run_result.evidence
    ]


def _extract_json_object(raw_output: str) -> dict[str, object]:
    stripped = raw_output.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("meta agent output did not contain a JSON object")
    decoded = json.loads(stripped[start : end + 1])
    if not isinstance(decoded, dict):
        raise ValueError("meta agent output must be a JSON object")
    return decoded


def _agent_trace(
    *,
    role_id: AgentModelRole,
    case: DebugCase,
    prompt: str,
    telemetry: MetaAgentTelemetry,
    payload: dict[str, object],
    raw_output: str,
) -> AgentTrace:
    return AgentTrace(
        agent_role=role_id,
        input_summary={
            "case_id": case.case_id,
            "task_type": case.task_type,
            "prompt_character_count": len(prompt),
            "model_provider": telemetry.model_provider,
            "model_id": telemetry.model_id,
            "status": telemetry.status,
        },
        input_excerpt=_clip_trace_text(prompt),
        input_sha256=_sha256_text(prompt),
        output_summary={
            "status": telemetry.status,
            "json_keys": sorted(str(key) for key in payload.keys()),
            "raw_output_character_count": len(raw_output),
            "latency_ms": telemetry.latency_ms,
            "total_tokens": telemetry.total_tokens,
            "estimated_cost_units": telemetry.estimated_cost_units,
            "error_message": telemetry.error_message,
        },
        output_excerpt=_clip_trace_text(raw_output),
        reasoning_summary=_reasoning_summary(
            role_id=role_id, payload=payload, error_message=telemetry.error_message
        ),
        raw_cot_policy="visible_output_summary_only",
    )


def _reasoning_summary(
    *,
    role_id: AgentModelRole,
    payload: dict[str, object],
    error_message: str,
) -> str:
    if error_message:
        return f"Agent fallback：{error_message}"
    if role_id == "report_root_cause":
        summary = payload.get("root_cause_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    if role_id == "experiment_planner":
        strategy = payload.get("strategy_updates")
        if isinstance(strategy, list):
            objectives = [
                str(item.get("objective", "")).strip()
                for item in strategy
                if isinstance(item, dict) and str(item.get("objective", "")).strip()
            ]
            if objectives:
                return "；".join(objectives[:3])
    if role_id == "judge_comparator":
        notes = payload.get("judge_comparison_notes")
        if isinstance(notes, list):
            summaries = [
                str(item.get("llm_note", "")).strip()
                for item in notes
                if isinstance(item, dict) and str(item.get("llm_note", "")).strip()
            ]
            if summaries:
                return "；".join(summaries[:3])
    return "Agent 返回了结构化 JSON，可见输出已保存在 output_excerpt；未采集隐藏 CoT。"


def _sha256_text(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clip_trace_text(value: str, limit: int = 4000) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def _estimated_cost_units(usage: dict[str, int | float]) -> float:
    total_tokens = usage.get("total_tokens", 0)
    if not isinstance(total_tokens, int | float):
        return 0.0
    return round(float(total_tokens) / 1000, 4)


def _string_dict(item: dict[object, object]) -> dict[str, str]:
    return {str(key): str(value) for key, value in item.items() if value is not None}

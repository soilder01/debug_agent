from __future__ import annotations

import hashlib

from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.reports.schemas import AgentTrace


def build_model_runner_agent_traces(run_result: ExperimentRunResult | None) -> list[AgentTrace]:
    if run_result is None:
        return []
    traces: list[AgentTrace] = []
    for evidence in run_result.evidence:
        input_summary = dict(evidence.request_summary)
        input_summary.setdefault("case_id", run_result.case_id)
        input_summary.setdefault("evidence_id", evidence.evidence_id)
        input_summary.setdefault("step_name", evidence.step_name)
        input_summary.setdefault("trial", evidence.trial)
        output_summary: dict[str, object] = {
            "evidence_id": evidence.evidence_id,
            "step_name": evidence.step_name,
            "trial": evidence.trial,
            "judge_score": evidence.judge.score,
            "judge_reasons": evidence.judge.reasons,
            "delta_count": len(evidence.judge.deltas),
            "model_provider": evidence.model_provider,
            "model_id": evidence.model_id,
            "model_name": evidence.model_name,
            "latency_ms": evidence.latency_ms,
            "usage": evidence.model_usage,
            "response_parse_error": evidence.response_parse_error,
            "model_call_error_type": evidence.model_call_error_type,
        }
        traces.append(
            AgentTrace(
                agent_role=str(input_summary.get("agent_role") or "model_runner"),
                input_summary=input_summary,
                input_excerpt=clip_trace_text(evidence.input_excerpt),
                input_sha256=sha256_text(evidence.input_excerpt),
                output_summary=output_summary,
                output_excerpt=clip_trace_text(evidence.raw_output),
                reasoning_summary=model_runner_reasoning_summary(evidence),
            )
        )
    return traces


def model_runner_reasoning_summary(evidence: ExperimentEvidence) -> str:
    if evidence.model_call_error_type:
        return f"模型调用失败：{evidence.model_call_error_type} {evidence.model_call_error_message}".strip()
    if evidence.response_parse_error:
        return f"输出解析失败：{evidence.response_parse_error}"
    reasons = ", ".join(evidence.judge.reasons)
    if reasons:
        return f"规则判分 score={evidence.judge.score}，原因：{reasons}"
    if evidence.judge.deltas:
        return f"规则判分 score={evidence.judge.score}，发现 {len(evidence.judge.deltas)} 个结构化差异。"
    return f"规则判分 score={evidence.judge.score}，未发现结构化差异。"


def sha256_text(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clip_trace_text(value: str, limit: int = 4000) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."

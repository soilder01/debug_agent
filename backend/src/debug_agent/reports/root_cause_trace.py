from __future__ import annotations

from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult

def _build_root_cause_trace(run_result: ExperimentRunResult | None) -> list[dict[str, object]]:
    if run_result is None:
        return []
    trace: list[dict[str, object]] = []
    for item in run_result.evidence:
        variant = _string_from_request_summary(item.request_summary.get("ablation_variant"))
        if variant:
            trace.append(_root_cause_trace_item(item=item, variant=variant))
        elif _has_timestamp_delta(item):
            trace.append(_root_cause_trace_item(item=item, variant="video_timestamp"))
    return trace


def _has_timestamp_delta(item: ExperimentEvidence) -> bool:
    return any(str(delta.get("reason", "")).startswith("timestamp_") for delta in item.judge.deltas)


def _root_cause_trace_item(item: ExperimentEvidence, variant: str) -> dict[str, object]:
    modalities = _string_list_from_request_summary(item.request_summary.get("ablation_modalities"))
    delta_reasons = _delta_reasons_from_evidence(item)
    target_ids = _target_ids_from_evidence(item)
    return {
        "step_name": item.step_name,
        "variant": variant,
        "modalities": modalities,
        "evidence_id": item.evidence_id,
        "judge_score": item.judge.score,
        "delta_reasons": delta_reasons,
        "target_ids": target_ids,
        "artifact_ids": [artifact.artifact_id for artifact in item.artifacts],
        "hypothesis": _trace_hypothesis(variant),
        "observation": _trace_observation(
            step_name=item.step_name,
            variant=variant,
            judge_score=item.judge.score,
            delta_reasons=delta_reasons,
            target_ids=target_ids,
        ),
        "conclusion": _trace_conclusion(variant=variant, judge_score=item.judge.score),
        "next_probe": _trace_next_probe(target_ids=target_ids, modalities=modalities),
    }


def _trace_hypothesis(variant: str) -> str:
    if variant == "video_timestamp":
        return "检查视频动作分段的 start_s/end_s 是否满足评分时间窗和连续性规则。"
    if variant == "cross_modal_compare":
        return "检查 cross_modal_compare 是否暴露跨模态对齐或融合问题。"
    return f"检查 {variant} 是否暴露该实验变体覆盖的能力问题。"


def _trace_observation(
    *,
    step_name: str,
    variant: str,
    judge_score: int,
    delta_reasons: list[str],
    target_ids: list[str],
) -> str:
    delta_summary = ", ".join(delta_reasons) if delta_reasons else "无"
    target_summary = ", ".join(target_ids) if target_ids else "无"
    return f"{step_name}/{variant} judge_score={judge_score}，delta={delta_summary}，target={target_summary}。"


def _trace_conclusion(*, variant: str, judge_score: int) -> str:
    outcome = "失败" if judge_score == 0 else "通过"
    if variant == "video_timestamp":
        return f"video_timestamp {outcome}，当前证据支持围绕视频时间边界定位继续归因。"
    return f"{variant} {outcome}，当前证据支持继续定位该变体覆盖的能力链路。"


def _trace_next_probe(*, target_ids: list[str], modalities: list[str]) -> str:
    target_summary = ", ".join(target_ids) if target_ids else "当前目标"
    if modalities:
        modality_summary = "/".join(modalities)
        return f"围绕 {target_summary} 执行 targeted evidence replay，并对比 {modality_summary} 单模态结果。"
    return f"围绕 {target_summary} 执行 targeted evidence replay，并补充对照实验。"


def _delta_reasons_from_evidence(evidence: ExperimentEvidence) -> list[str]:
    return sorted(
        {
            str(delta["reason"])
            for delta in evidence.judge.deltas
            if isinstance(delta.get("reason"), str) and str(delta.get("reason")).strip()
        }
    )


def _target_ids_from_evidence(evidence: ExperimentEvidence) -> list[str]:
    return sorted(
        {
            str(delta["target_id"])
            for delta in evidence.judge.deltas
            if isinstance(delta.get("target_id"), str) and str(delta.get("target_id")).strip()
        }
        | {
            token
            for reason in evidence.judge.reasons
            for token in _target_id_tokens_from_reason(reason)
        }
    )


def _target_id_tokens_from_reason(reason: str) -> set[str]:
    return {
        token.strip(".,;，；。()[]{}")
        for token in reason.split()
        if _looks_like_target_id(token.strip(".,;，；。()[]{}"))
    }


def _looks_like_target_id(value: str) -> bool:
    return value.startswith(("image:region:", "video:segment:", "multimodal:conflict:", "box:"))


def _string_from_request_summary(value: object) -> str:
    return value if isinstance(value, str) and value.strip() else ""


def _string_list_from_request_summary(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []

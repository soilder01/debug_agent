from __future__ import annotations

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import (
    plan_experiments,
    plan_strategy_follow_up_experiments,
    plan_targeted_probe_experiments,
    plan_verification_follow_up_experiments,
)
from debug_agent.reports.schemas import RootCause

def _build_debug_strategy(
    *,
    root_cause: RootCause,
    citation_context: dict[str, str],
) -> list[dict[str, str]]:
    if root_cause.label == "cross_modal_alignment_failure":
        return [
            {
                "stage": "evidence_audit",
                "objective": "确认当前 root cause 是否有足够 evidence/artifact 支撑。",
                "trigger": "root_cause=cross_modal_alignment_failure",
                "planned_probe": (
                    f"复查 {citation_context['evidence_ids']} 和关联产物，确认失败目标与 delta 是否一致。"
                ),
                "stop_condition": "关键 target、delta reason、artifact citation 能共同解释当前失败。",
                "escalation": "如果证据链不完整，先补充 targeted evidence replay，而不是直接归因模型能力。",
            },
            {
                "stage": "ablation_expansion",
                "objective": "验证跨模态失败是否稳定复现，且不是单模态感知失败。",
                "trigger": f"trace_refs={citation_context['trace_refs']}",
                "planned_probe": "对比 image/text 单模态结果与 cross_modal_compare 结果，必要时加入 conflict_grounding_check。",
                "stop_condition": "单模态通过且 cross-modal probe 失败时，确认跨模态对齐/融合链路为主因。",
                "escalation": "如果单模态也失败，切换到 single_modality_capability_gap 策略。",
            },
            {
                "stage": "verification_gate",
                "objective": "验证推荐操作是否真正改善 badcase，而非只改善报告描述。",
                "trigger": "recommended_actions_present",
                "planned_probe": "将 applied 推荐操作提交 verification job，并比较 source/verification success rate。",
                "stop_condition": "verification result 为 resolved，且未出现 regressed。",
                "escalation": "若 verification 为 not_resolved/regressed，自动生成 follow-up probing plan。",
            },
        ]
    if root_cause.label in {
        "single_modality_capability_gap",
        "prompt_schema_issue",
        "scoring_standard_issue",
    }:
        return [
            {
                "stage": "evidence_audit",
                "objective": "确认当前诊断是否有足够 evidence 或评测资产信号支撑。",
                "trigger": f"root_cause={root_cause.label}",
                "planned_probe": f"复查 {citation_context['evidence_ids'] or '当前样本'}，确认诊断信号是否可复现。",
                "stop_condition": "证据链、评测资产诊断和推荐操作能够互相印证。",
                "escalation": "如果证据不足，优先补充 targeted replay 或人工标注核验。",
            }
        ]
    return []


def _build_follow_up_experiments(
    case: DebugCase,
    verification_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    follow_ups: list[dict[str, str]] = []
    for verification_result in verification_results:
        result = verification_result.get("result")
        verification_job_id = verification_result.get("verification_job_id")
        if result not in {"not_resolved", "regressed"} or not isinstance(verification_job_id, str):
            continue
        follow_up_plan = plan_verification_follow_up_experiments(case, verification_result)
        planned_steps = ", ".join(step.name for step in follow_up_plan.steps)
        follow_ups.append(
            {
                "source": "verification_result",
                "verification_job_id": verification_job_id,
                "result": str(result),
                "planned_steps": planned_steps,
                "summary": (
                    f"验证任务 {verification_job_id} 结果为 {result}，"
                    f"建议执行 {len(follow_up_plan.steps)} 个后续 probing 步骤。"
                ),
            }
        )
    return follow_ups


def _build_strategy_follow_up_experiments(
    *,
    case: DebugCase,
    debug_strategy: list[dict[str, str]],
) -> list[dict[str, str]]:
    base_step_names = {step.name for step in plan_experiments(case).steps}
    strategy_plan = plan_strategy_follow_up_experiments(case, debug_strategy)
    follow_up_steps = [step for step in strategy_plan.steps if step.name not in base_step_names]
    return [
        {
            "source": "debug_strategy",
            "stage": stage,
            "planned_steps": step.name,
            "summary": f"策略阶段 {stage} 已转为 follow-up experiment：{step.name}。",
        }
        for step in follow_up_steps
        if (stage := step.name.removeprefix("strategy_").removesuffix("_probe"))
    ]


def _build_targeted_probe_follow_up_experiments(
    *,
    case: DebugCase,
    root_cause_trace: list[dict[str, object]],
) -> list[dict[str, str]]:
    base_step_names = {step.name for step in plan_experiments(case).steps}
    targeted_plan = plan_targeted_probe_experiments(case, root_cause_trace)
    targeted_steps = [step for step in targeted_plan.steps if step.name not in base_step_names]
    targeted_step_names = {step.name for step in targeted_steps}
    target_ids: list[str] = []
    for trace in root_cause_trace:
        trace_target_ids = trace.get("target_ids")
        if not isinstance(trace_target_ids, list):
            continue
        target_ids.extend(
            target_id
            for target_id in trace_target_ids
            if isinstance(target_id, str) and _targeted_step_name(target_id) in targeted_step_names
        )
    return [
        {
            "source": "targeted_probe",
            "target_id": target_id,
            "planned_steps": step.name,
            "summary": f"围绕目标 {target_id} 生成 targeted probing：{step.name}。",
        }
        for target_id, step in zip(target_ids, targeted_steps, strict=False)
    ]


def _targeted_step_name(target_id: str) -> str:
    if target_id.startswith("image:region:"):
        return "targeted_image_region_probe"
    if target_id.startswith("video:segment:"):
        return "targeted_video_segment_probe"
    if target_id.startswith("multimodal:conflict:"):
        return "targeted_multimodal_conflict_probe"
    return ""

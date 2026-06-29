from __future__ import annotations

from debug_agent.reports.citations import with_citations
from debug_agent.reports.schemas import RootCause

def build_recommended_actions(
    root_cause: RootCause,
    *,
    citation_context: dict[str, str],
) -> list[dict[str, str]]:
    if root_cause.label == "scoring_standard_issue":
        return with_citations(
            {
                "category": "evaluation_asset",
                "priority": "high",
                "status": "pending",
                "summary": "补齐评分标准。",
                "detail": "补充 exact match、可接受别字/格式、box_id 对齐等评分规则，避免 0/1 结论不可审计。",
            },
            citation_context,
        )
    if root_cause.label == "golden_answer_issue":
        return with_citations(
            {
                "category": "evaluation_asset",
                "priority": "high",
                "status": "pending",
                "summary": "补齐标答。",
                "detail": "补充至少一个可评分目标、区域或结构化字段，并确保 golden answer 与样本输入一致。",
            },
            citation_context,
        )
    if root_cause.label == "expected_output_issue":
        return with_citations(
            {
                "category": "evaluation_asset",
                "priority": "high",
                "status": "pending",
                "summary": "补齐通用任务 expected_output。",
                "detail": "补充 task-native expected_output_json，明确分类、检测、视频片段或多模态冲突的期望结构。",
            },
            citation_context,
        )
    if root_cause.label == "prompt_schema_issue":
        return with_citations(
            {
                "category": "prompt",
                "priority": "high",
                "status": "pending",
                "summary": "明确结构化输出 schema。",
                "detail": "要求模型只输出可解析 JSON，并声明关键字段、类型和禁止额外文本。",
            },
            citation_context,
        )
    if root_cause.label == "video_timestamp_boundary_error":
        return with_citations(
            [
                {
                    "category": "prompt",
                    "priority": "high",
                    "status": "pending",
                    "summary": "补强视频时序边界定位。",
                    "detail": "要求模型先逐段确认动作开始、结束事件和目标物释放/离开时刻，再输出 video_action_segments JSON。",
                },
                {
                    "category": "evaluation_asset",
                    "priority": "medium",
                    "status": "pending",
                    "summary": "复核 timestamp grids 与子任务标签一致性。",
                    "detail": "检查 check_timestamp 的 range/continue 规则是否与参考答案、prompt 子任务数量和动作定义严格对齐。",
                },
                {
                    "category": "model_capability",
                    "priority": "high",
                    "status": "pending",
                    "summary": "加入视频时序边界回归集。",
                    "detail": "将该样本纳入 temporal boundary regression，重点监控 end_s 是否持续落在期望窗口内。",
                },
            ],
            citation_context,
        )
    if root_cause.label == "single_modality_capability_gap":
        modality = _modality_from_root_cause_summary(root_cause.evidence_summary)
        return with_citations(
            [
                {
                    "category": "prompt",
                    "priority": "high",
                    "status": "pending",
                    "summary": f"强化 {modality} 模态定位与证据引用要求。",
                    "detail": f"在 prompt 中要求模型先列出 {modality} 证据、目标区域或关键帧，再输出最终结构化结论。",
                },
                {
                    "category": "evaluation_asset",
                    "priority": "medium",
                    "status": "pending",
                    "summary": f"补充 {modality} 单模态 golden evidence。",
                    "detail": f"为失败样本补充 {modality}-only 期望证据、区域/关键帧标注或可接受视觉解释，避免跨模态结论缺少单模态审计依据。",
                },
                {
                    "category": "model_capability",
                    "priority": "high",
                    "status": "pending",
                    "summary": f"将 {modality} 感知能力短板纳入模型能力归因。",
                    "detail": f"单模态 ablation 已失败，优先归因 {modality} 感知/定位/grounding 能力，而不是跨模态融合。",
                },
            ],
            citation_context,
        )
    if root_cause.label == "cross_modal_alignment_failure":
        return with_citations(
            [
                {
                    "category": "prompt",
                    "priority": "high",
                    "status": "pending",
                    "summary": "强化跨模态对比步骤。",
                    "detail": "要求模型先分别列出 image/text 证据，再输出冲突结论。",
                },
                {
                    "category": "evaluation_asset",
                    "priority": "medium",
                    "status": "pending",
                    "summary": "补充跨模态冲突 golden evidence。",
                    "detail": "为样本补充各模态独立证据和最终冲突标注，便于判断融合错误还是标注问题。",
                },
                {
                    "category": "model_capability",
                    "priority": "high",
                    "status": "pending",
                    "summary": "将跨模态融合短板纳入模型能力归因。",
                    "detail": "单模态通过但跨模态失败，优先检查 fusion/alignment 能力。",
                },
            ],
            citation_context,
        )
    return []


def _modality_from_root_cause_summary(summary: str) -> str:
    for modality in ["image", "text", "video", "audio"]:
        if modality in summary:
            return modality
    return "target"

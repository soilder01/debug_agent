from dataclasses import dataclass


@dataclass(frozen=True)
class ReportTaxonomyProfile:
    structured_mismatch_label: str
    fallback_failure_type: str
    fallback_summary: str
    fallback_root_cause_label: str
    fallback_evidence_summary: str
    fallback_sheet_reason: str


HANDWRITING_OCR_TAXONOMY = ReportTaxonomyProfile(
    structured_mismatch_label="answer_mismatch",
    fallback_failure_type="erasure_revision_failure",
    fallback_summary="模型在涂改、错字或相近字符场景下存在语义猜测和纠偏风险。",
    fallback_root_cause_label="erasure_revision_failure",
    fallback_evidence_summary="当前样本低分且人工备注指向涂改区域识别失败，需要复测确认。",
    fallback_sheet_reason="模型无法稳定识别涂改后的最终答案，存在语义补全倾向。",
)

GENERIC_TAXONOMY = ReportTaxonomyProfile(
    structured_mismatch_label="output_mismatch",
    fallback_failure_type="output_mismatch",
    fallback_summary="通用检测任务存在模型输出与期望结果不一致，需要复测确认。",
    fallback_root_cause_label="output_mismatch",
    fallback_evidence_summary="通用检测任务低分或不稳定，需要结合 evidence、prompt、标答和评分标准继续确认。",
    fallback_sheet_reason="通用检测任务输出与期望结果不一致，需要进一步定位模型、prompt 或评测资产问题。",
)


def taxonomy_for_task_type(task_type: str) -> ReportTaxonomyProfile:
    if task_type == "handwriting_ocr":
        return HANDWRITING_OCR_TAXONOMY
    return GENERIC_TAXONOMY

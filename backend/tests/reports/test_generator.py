import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.judging.runner import JudgeResult
from debug_agent.reports.generator import generate_initial_report


def test_generate_initial_report_for_failed_case() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)

    report = generate_initial_report(case, plan)

    assert report.case_id == "handwrite233"
    assert report.status == "needs_human_review"
    assert report.root_cause.label == "erasure_revision_failure"
    assert report.suggested_sheet_fields["debug1状态"] == "待人工确认"


def test_generate_initial_report_uses_generic_fallback_for_non_ocr_case() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-1",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"negative\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)

    report = generate_initial_report(case, plan)

    assert report.observed_failure.type == "output_mismatch"
    assert report.root_cause.label == "output_mismatch"
    assert "涂改" not in report.observed_failure.summary
    assert "通用检测任务" in report.root_cause.evidence_summary


def test_generate_report_includes_experiment_summary() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e1",
                step_name="baseline_replay",
                trial=0,
                image_artifacts=[
                    {
                        "artifact_id": "case-1:box-7:localized-candidate",
                        "kind": "affected_box_candidate",
                        "source_image_uri": "file:///tmp/case-1.png",
                    }
                ],
                artifacts=[
                    {
                        "artifact_id": "case-1:baseline:0:input-snapshot",
                        "kind": "input_snapshot",
                        "artifact_type": "request",
                        "source_uri": "file:///tmp/case-1.png",
                        "derived_uri": "",
                        "preview_url": "",
                        "region": None,
                        "metadata": {"task_type": "handwriting_ocr"},
                    }
                ],
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 1 student_answer_mismatch"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.total_trials == 1
    assert report.experiment_summary.success_count == 0
    assert report.experiment_summary.evidence_ids == ["e1"]
    assert report.experiment_summary.image_artifact_ids == ["case-1:box-7:localized-candidate"]
    assert report.experiment_summary.artifact_ids == ["case-1:baseline:0:input-snapshot"]
    assert report.experiment_summary.artifact_evidence_links == [
        {
            "artifact_id": "case-1:baseline:0:input-snapshot",
            "evidence_id": "e1",
        },
        {
            "artifact_id": "case-1:box-7:localized-candidate",
            "evidence_id": "e1",
        }
    ]


def test_generate_report_summarizes_replay_stability() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=1,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-pass",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-1",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 1 student_answer_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-2",
                step_name="baseline_replay",
                trial=2,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 2 student_answer_mismatch"]),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.failed_trial_count == 2
    assert report.experiment_summary.success_rate == 1 / 3
    assert report.experiment_summary.stability_label == "unstable"


def test_generate_report_groups_experiment_results_by_step() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=1,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-baseline-pass",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                artifacts=[
                    {
                        "artifact_id": "baseline:input",
                        "kind": "input_snapshot",
                        "artifact_type": "request",
                    }
                ],
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-baseline-fail",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                artifacts=[
                    {
                        "artifact_id": "baseline:delta",
                        "kind": "image_region_delta",
                        "artifact_type": "image_region",
                    }
                ],
                judge=JudgeResult(
                    score=0,
                    reasons=["image:region:1 region_label_mismatch"],
                    deltas=[
                        {
                            "target_id": "image:region:1",
                            "expected": "cat",
                            "actual": "dog",
                            "reason": "region_label_mismatch",
                            "metadata": {"field": "label"},
                        }
                    ],
                ),
            ),
            ExperimentEvidence(
                evidence_id="e-ablation-fail",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={
                    "ablation_variant": "text_only",
                    "ablation_modalities": ["text"],
                },
                raw_output=case.predictions[0].raw_output,
                artifacts=[
                    {
                        "artifact_id": "ablation:delta",
                        "kind": "multimodal_conflict_delta",
                        "artifact_type": "multimodal_conflict",
                    }
                ],
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                    deltas=[
                        {
                            "target_id": "multimodal:conflict:1",
                            "expected": "same",
                            "actual": "different",
                            "reason": "conflict_actual_mismatch",
                            "metadata": {"field": "actual"},
                        }
                    ],
                ),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.step_summaries == [
        {
            "step_name": "baseline_replay",
            "total_trials": 2,
            "success_count": 1,
            "failed_trial_count": 1,
            "success_rate": 0.5,
            "delta_reasons": ["region_label_mismatch"],
            "target_ids": ["image:region:1"],
            "evidence_ids": ["e-baseline-pass", "e-baseline-fail"],
            "artifact_ids": ["baseline:input", "baseline:delta"],
        },
        {
            "step_name": "modality_ablation_check",
            "total_trials": 1,
            "success_count": 0,
            "failed_trial_count": 1,
            "success_rate": 0.0,
            "delta_reasons": ["conflict_actual_mismatch"],
            "target_ids": ["multimodal:conflict:1"],
            "evidence_ids": ["e-ablation-fail"],
            "artifact_ids": ["ablation:delta"],
            "ablation_variants": ["text_only"],
            "ablation_modalities": ["text"],
        },
    ]


def test_generate_report_infers_root_cause_from_structured_judge_deltas() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-structured",
                step_name="baseline_replay",
                trial=0,
                image_artifacts=[
                    {
                        "artifact_id": "case-1:box-7:localized-candidate",
                        "kind": "affected_box_candidate",
                        "source_image_uri": "file:///tmp/case-1.png",
                    }
                ],
                artifacts=[
                    {
                        "artifact_id": "case-1:baseline:0:input-snapshot",
                        "kind": "input_snapshot",
                        "artifact_type": "request",
                        "source_uri": "file:///tmp/case-1.png",
                        "derived_uri": "",
                        "preview_url": "",
                        "region": None,
                        "metadata": {"task_type": "handwriting_ocr"},
                    }
                ],
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["box 7 student_answer_mismatch"],
                    scoring_standard=case.scoring_standard,
                    affected_box_ids=[7],
                    deltas=[
                        {
                            "target_id": "box:7",
                            "expected": "低昷烘干",
                            "actual": "低温烘干",
                            "reason": "student_answer_mismatch",
                            "metadata": {
                                "box_id": 7,
                                "field": "student_answer",
                                "legacy_reason": "student_answer_mismatch",
                            },
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "answer_mismatch"
    assert report.observed_failure.affected_box_ids == [7]
    assert "box 7" in report.observed_failure.summary
    assert report.root_cause.label == "answer_mismatch"
    assert report.root_cause.confidence == "high"
    assert "student_answer_mismatch" in report.root_cause.evidence_summary
    assert "box 7" in report.suggested_sheet_fields["错误原因"]
    assert report.evidence_citations == [
        {
            "evidence_id": "e-structured",
            "step_name": "baseline_replay",
            "box_id": 7,
            "reason": "student_answer_mismatch",
            "artifact_ids": ["case-1:baseline:0:input-snapshot"],
        }
    ]


def test_generate_report_infers_cross_modal_alignment_from_ablation_results() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-ablation-root-cause",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches image",
                        "actual": "caption says cat but image shows dog",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=2,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-image-only",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-cross-modal",
                step_name="modality_ablation_check",
                trial=2,
                request_summary={
                    "ablation_variant": "cross_modal_compare",
                    "ablation_modalities": ["image", "text"],
                },
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                    deltas=[
                        {
                            "target_id": "multimodal:conflict:1",
                            "expected": "caption matches image",
                            "actual": "caption says cat but image shows dog",
                            "reason": "conflict_actual_mismatch",
                            "metadata": {
                                "field": "actual",
                                "expected_modalities": ["image", "text"],
                                "actual_modalities": ["image", "text"],
                            },
                        }
                    ],
                ),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "cross_modal_alignment_failure"
    assert "单模态变体可通过" in report.observed_failure.summary
    assert report.root_cause.label == "cross_modal_alignment_failure"
    assert report.root_cause.confidence == "high"
    assert "image_only, text_only" in report.root_cause.evidence_summary
    assert "cross_modal_compare" in report.root_cause.evidence_summary
    assert report.confidence_reasons == [
        {
            "source": "evidence_count",
            "level": "high",
            "summary": "3 条 evidence 支撑当前判断。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
        {
            "source": "ablation_pattern",
            "level": "high",
            "summary": "root cause trace 包含 cross_modal_compare 变体，支持跨模态归因。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
        {
            "source": "verification_outcome",
            "level": "neutral",
            "summary": "尚无验证任务结果参与置信度判断。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
    ]
    assert report.suggested_sheet_fields["错误原因"].startswith("跨模态对齐问题")
    assert report.suggested_sheet_fields["Ablation结论"] == (
        "单模态变体 image_only, text_only 可通过，但跨模态变体 cross_modal_compare 失败。"
    )
    assert report.debug_strategy == [
        {
            "stage": "evidence_audit",
            "objective": "确认当前 root cause 是否有足够 evidence/artifact 支撑。",
            "trigger": "root_cause=cross_modal_alignment_failure",
            "planned_probe": "复查 e-image-only, e-text-only, e-cross-modal 和关联产物，确认失败目标与 delta 是否一致。",
            "stop_condition": "关键 target、delta reason、artifact citation 能共同解释当前失败。",
            "escalation": "如果证据链不完整，先补充 targeted evidence replay，而不是直接归因模型能力。",
        },
        {
            "stage": "ablation_expansion",
            "objective": "验证跨模态失败是否稳定复现，且不是单模态感知失败。",
            "trigger": "trace_refs=modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
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
    expected_strategy_follow_ups = [
        {
            "source": "debug_strategy",
            "stage": "evidence_audit",
            "planned_steps": "strategy_evidence_audit_probe",
            "summary": "策略阶段 evidence_audit 已转为 follow-up experiment：strategy_evidence_audit_probe。",
        },
        {
            "source": "debug_strategy",
            "stage": "ablation_expansion",
            "planned_steps": "strategy_ablation_expansion_probe",
            "summary": "策略阶段 ablation_expansion 已转为 follow-up experiment：strategy_ablation_expansion_probe。",
        },
        {
            "source": "debug_strategy",
            "stage": "verification_gate",
            "planned_steps": "strategy_verification_gate_probe",
            "summary": "策略阶段 verification_gate 已转为 follow-up experiment：strategy_verification_gate_probe。",
        },
    ]
    for follow_up in expected_strategy_follow_ups:
        assert follow_up in report.follow_up_experiments
    assert {
        "source": "targeted_probe",
        "target_id": "multimodal:conflict:1",
        "planned_steps": "targeted_multimodal_conflict_probe",
        "summary": "围绕目标 multimodal:conflict:1 生成 targeted probing：targeted_multimodal_conflict_probe。",
    } in report.follow_up_experiments


def test_generate_report_infers_single_modality_gap_from_ablation_results() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "image-ablation-root-cause",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches image",
                        "actual": "caption says cat but image shows dog",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=1,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-image-only",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                    deltas=[
                        {
                            "target_id": "multimodal:conflict:1",
                            "expected": "dog",
                            "actual": "cat",
                            "reason": "conflict_actual_mismatch",
                            "metadata": {"field": "actual", "actual_modalities": ["image"]},
                        }
                    ],
                ),
            ),
            ExperimentEvidence(
                evidence_id="e-text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-cross-modal",
                step_name="modality_ablation_check",
                trial=2,
                request_summary={
                    "ablation_variant": "cross_modal_compare",
                    "ablation_modalities": ["image", "text"],
                },
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "single_modality_capability_gap"
    assert "image_only" in report.observed_failure.summary
    assert report.root_cause.label == "single_modality_capability_gap"
    assert report.root_cause.confidence == "high"
    assert "image_only" in report.root_cause.evidence_summary
    assert report.suggested_sheet_fields["错误原因"].startswith("单模态能力短板")
    assert report.suggested_sheet_fields["Ablation结论"] == (
        "单模态变体 image_only 失败，优先检查 image 模态感知能力。"
    )
    assert report.recommended_actions == [
        {
            "category": "prompt",
            "priority": "high",
            "status": "pending",
            "summary": "强化 image 模态定位与证据引用要求。",
            "detail": "在 prompt 中要求模型先列出 image 证据、目标区域或关键帧，再输出最终结构化结论。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
        {
            "category": "evaluation_asset",
            "priority": "medium",
            "status": "pending",
            "summary": "补充 image 单模态 golden evidence。",
            "detail": "为失败样本补充 image-only 期望证据、区域/关键帧标注或可接受视觉解释，避免跨模态结论缺少单模态审计依据。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
        {
            "category": "model_capability",
            "priority": "high",
            "status": "pending",
            "summary": "将 image 感知能力短板纳入模型能力归因。",
            "detail": "单模态 ablation 已失败，优先归因 image 感知/定位/grounding 能力，而不是跨模态融合。",
            "evidence_ids": "e-image-only, e-text-only, e-cross-modal",
            "artifact_ids": "",
            "trace_refs": "modality_ablation_check:image_only, modality_ablation_check:text_only, modality_ablation_check:cross_modal_compare",
        },
    ]


def test_generate_report_builds_ablation_root_cause_trace() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "ablation-trace",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches image",
                        "actual": "caption says cat but image shows dog",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-cross-modal",
                step_name="modality_ablation_check",
                trial=2,
                request_summary={
                    "ablation_variant": "cross_modal_compare",
                    "ablation_modalities": ["image", "text"],
                },
                raw_output=case.predictions[0].raw_output,
                artifacts=[
                    {
                        "artifact_id": "ablation:conflict:delta",
                        "kind": "multimodal_conflict_delta",
                        "artifact_type": "multimodal_conflict",
                    }
                ],
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                    deltas=[
                        {
                            "target_id": "multimodal:conflict:1",
                            "expected": "caption matches image",
                            "actual": "caption says cat but image shows dog",
                            "reason": "conflict_actual_mismatch",
                            "metadata": {"field": "actual"},
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.root_cause_trace == [
        {
            "step_name": "modality_ablation_check",
            "variant": "cross_modal_compare",
            "modalities": ["image", "text"],
            "evidence_id": "e-cross-modal",
            "judge_score": 0,
            "delta_reasons": ["conflict_actual_mismatch"],
            "target_ids": ["multimodal:conflict:1"],
            "artifact_ids": ["ablation:conflict:delta"],
            "hypothesis": "检查 cross_modal_compare 是否暴露跨模态对齐或融合问题。",
            "observation": (
                "modality_ablation_check/cross_modal_compare judge_score=0，"
                "delta=conflict_actual_mismatch，target=multimodal:conflict:1。"
            ),
            "conclusion": "cross_modal_compare 失败，当前证据支持继续定位该变体覆盖的能力链路。",
            "next_probe": "围绕 multimodal:conflict:1 执行 targeted evidence replay，并对比 image/text 单模态结果。",
        }
    ]
    assert {
        "source": "targeted_probe",
        "target_id": "multimodal:conflict:1",
        "planned_steps": "targeted_multimodal_conflict_probe",
        "summary": "围绕目标 multimodal:conflict:1 生成 targeted probing：targeted_multimodal_conflict_probe。",
    } in report.follow_up_experiments


def test_generate_report_includes_verification_follow_up_plan_summary() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "report-verification-follow-up",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/video.mp4",
            "prompt": "Detect events and return temporal segment JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "temporal_segments": [
                    {"target_id": "video:segment:1", "start_ms": 1000, "end_ms": 2500, "label": "person_enters"}
                ]
            },
            "scoring_standard": "temporal segment target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"temporal_segments\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)

    report = generate_initial_report(
        case,
        plan,
        verification_results=[
            {
                "verification_job_id": "job-verify-video",
                "result": "regressed",
                "summary": "验证任务通过率 0%，低于原任务 50%，推荐操作可能引入回归。",
            }
        ],
    )

    assert report.verification_results == [
        {
            "verification_job_id": "job-verify-video",
            "result": "regressed",
            "summary": "验证任务通过率 0%，低于原任务 50%，推荐操作可能引入回归。",
        }
    ]
    assert report.follow_up_experiments == [
        {
            "source": "verification_result",
            "verification_job_id": "job-verify-video",
            "result": "regressed",
            "planned_steps": (
                "baseline_replay, temporal_schema_check, temporal_grounding_check, verification_regression_probe"
            ),
            "summary": "验证任务 job-verify-video 结果为 regressed，建议执行 4 个后续 probing 步骤。",
        }
    ]
    assert {
        "source": "verification_outcome",
        "level": "low",
        "summary": "验证任务出现 regressed，降低当前推荐操作置信度。",
        "evidence_ids": "",
        "artifact_ids": "",
        "trace_refs": "",
    } in report.confidence_reasons


def test_generate_report_uses_generic_output_mismatch_for_non_ocr_structured_deltas() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-structured",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"negative\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-classification",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["label mismatch"],
                    scoring_standard=case.scoring_standard,
                    deltas=[
                        {
                            "target_id": "label:sentiment",
                            "expected": "positive",
                            "actual": "negative",
                            "reason": "label_mismatch",
                            "metadata": {"field": "sentiment"},
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "output_mismatch"
    assert report.root_cause.label == "output_mismatch"
    assert "label:sentiment" in report.root_cause.evidence_summary
    assert "结构化评分差异指向 label:sentiment" in report.root_cause.evidence_summary
    assert "Structured judge deltas" not in report.root_cause.evidence_summary
    assert "box" not in report.observed_failure.summary
    assert report.suggested_sheet_fields["影响目标"] == "label:sentiment"
    assert report.suggested_sheet_fields["结构化差异"] == "label:sentiment label_mismatch: expected=positive actual=negative"


def test_generate_report_uses_parse_error_when_schema_prompt_still_fails_to_parse() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-parse",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "not-json", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-parse",
                step_name="baseline_replay",
                trial=0,
                response_parse_error="Expecting value",
                raw_output="not-json",
                judge=JudgeResult(score=0, reasons=["response_parse_error"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "parse_error"
    assert report.root_cause.label == "parse_error"
    assert "解析失败" in report.root_cause.evidence_summary


def test_generate_report_uses_unstable_prediction_for_mixed_success_without_deltas() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-unstable",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"answers\":[]}", "score": 0}],
            "avg_score": 0.33,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=1,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-pass",
                step_name="baseline_replay",
                trial=0,
                raw_output="{\"answers\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-1",
                step_name="baseline_replay",
                trial=1,
                raw_output="{\"answers\":[]}",
                judge=JudgeResult(score=0, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-2",
                step_name="baseline_replay",
                trial=2,
                raw_output="{\"answers\":[]}",
                judge=JudgeResult(score=0, reasons=[]),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "unstable_prediction"
    assert report.root_cause.label == "unstable_prediction"
    assert "1/3" in report.root_cause.evidence_summary


def test_generate_report_adds_native_target_and_artifact_fields_for_multimodal_deltas() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-writeback",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-multimodal",
                step_name="baseline_replay",
                trial=0,
                artifacts=[
                    {
                        "artifact_id": "multimodal-writeback:baseline:0:input-snapshot",
                        "kind": "input_snapshot",
                        "artifact_type": "request",
                        "source_uri": "file:///tmp/multimodal.mp4",
                        "derived_uri": "",
                        "preview_url": "",
                        "region": None,
                        "metadata": {"task_type": "multimodal_detection"},
                    }
                ],
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                    scoring_standard=case.scoring_standard,
                    deltas=[
                        {
                            "target_id": "multimodal:conflict:1",
                            "expected": "image and caption both describe a cat",
                            "actual": "image shows dog while caption says cat",
                            "reason": "conflict_actual_mismatch",
                            "metadata": {
                                "field": "actual",
                                "conflict_type": "visual_text_conflict",
                                "modalities": ["image", "text"],
                                "confidence": 0.76,
                            },
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.suggested_sheet_fields["影响目标"] == "multimodal:conflict:1"
    assert report.suggested_sheet_fields["结构化差异"] == (
        "multimodal:conflict:1 conflict_actual_mismatch: "
        "expected=image and caption both describe a cat actual=image shows dog while caption says cat"
    )
    assert report.suggested_sheet_fields["证据产物"] == "multimodal-writeback:baseline:0:input-snapshot"


def test_generate_report_explains_video_timestamp_deltas_in_chinese() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "video-timestamp-report",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/jszn-131.mp4",
            "prompt": "Return video_action_segments JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "temporal_segments": [
                    {
                        "target_id": "video:segment:1",
                        "start_ms": 100,
                        "end_ms": 24000,
                        "label": "The right arm picks up the crab clamp and adjusts its position",
                    }
                ]
            },
            "scoring_standard": "check_timestamp",
            "predictions": [{"trial": 0, "raw_output": "{}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-video-timestamp",
                step_name="temporal_schema_check",
                trial=0,
                artifacts=[
                    {
                        "artifact_id": "video-timestamp-report:temporal_schema_check:0:video_segment_1:delta",
                        "kind": "video_segment_delta",
                        "artifact_type": "video_segment",
                        "source_uri": "file:///tmp/jszn-131.mp4",
                        "metadata": {
                            "target_id": "video:segment:1",
                            "reason": "timestamp_end_out_of_range",
                            "expected_end_s_range": "22.0-24.0",
                            "actual_end_s": 34.0,
                            "delta_seconds": 10.0,
                        },
                    }
                ],
                raw_output="{}",
                judge=JudgeResult(
                    score=0,
                    reasons=["video:segment:1 timestamp_end_out_of_range"],
                    deltas=[
                        {
                            "target_id": "video:segment:1",
                            "expected": "22.0-24.0s",
                            "actual": "34.0s",
                            "reason": "timestamp_end_out_of_range",
                            "metadata": {
                                "field": "end_s",
                                "expected_end_s_range": "22.0-24.0",
                                "actual_end_s": 34.0,
                                "delta_seconds": 10.0,
                            },
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.root_cause.label == "video_timestamp_boundary_error"
    assert report.root_cause_trace[0]["variant"] == "video_timestamp"
    assert report.root_cause_trace[0]["target_ids"] == ["video:segment:1"]
    assert "视频时间边界定位失败" in report.root_cause.evidence_summary
    assert report.suggested_sheet_fields["错误原因"] == "视频时间边界定位失败：video:segment:1 end_s 超出期望窗口 22.0-24.0s，实际 34.0s，偏差 10.0s。"
    assert "video:segment:1 end_s 超出期望窗口 22.0-24.0s，实际 34.0s，偏差 10.0s" in report.suggested_sheet_fields["结构化差异"]
    assert report.recommended_actions[0]["summary"] == "补强视频时序边界定位。"


def test_generate_report_prioritizes_runtime_failures_before_answer_mismatch() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-timeout",
                step_name="baseline_replay",
                trial=0,
                model_call_error_type="TimeoutError",
                model_call_error_message="model request timed out",
                raw_output="",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "model_call_error"
    assert report.root_cause.label == "model_call_error"
    assert report.root_cause.confidence == "high"
    assert "TimeoutError" in report.root_cause.evidence_summary


def test_generate_report_uses_lark_badcase_context_when_source_replay_fails() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "lark-draft-video-1",
            "task_type": "generic_json",
            "image_uri": "file:///tmp/JSZN-131.mp4",
            "prompt": "Debug this enterprise badcase. Return JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "reference_answer": {
                    "video_action_segments": [
                        {"subtask_label": "pick sponge", "start_s": 23.2, "end_s": 43.5}
                    ]
                }
            },
            "output_schema": {},
            "scoring_standard": "timestamp must match expected window.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"video_action_segments\":[{\"subtask_label\":\"pick sponge\",\"start_s\":34.1,\"end_s\":48.0}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "human_notes": {
                "debug_status": "from_lark_badcase_draft",
                "root_cause": "EvalOpCheckTimestamp 失败：clip 0 end_s 不在范围内",
            },
        }
    )
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-source-replay-error",
                step_name="baseline_replay",
                trial=0,
                model_call_error_type="URLError",
                model_call_error_message="EOF occurred in violation of protocol",
                raw_output="",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "video_timestamp_mismatch"
    assert report.root_cause.label == "video_timestamp_boundary_error"
    assert report.root_cause.confidence == "medium"
    assert "表格提供的原始模型输出" in report.root_cause.evidence_summary
    assert "source replay 调用失败" in report.suggested_sheet_fields["模型复测诊断"]
    assert report.suggested_sheet_fields["错误原因"].startswith("视频时间边界定位失败")


def test_generate_report_flags_missing_scoring_standard_as_evaluation_asset_issue() -> None:
    case = _diagnostic_case(scoring_standard="")
    plan = plan_experiments(case)
    run_result = _one_failed_answer_mismatch_result(case)

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "evaluation_asset_issue"
    assert report.root_cause.label == "scoring_standard_issue"
    assert report.root_cause.confidence == "high"
    assert "评分标准缺失" in report.root_cause.evidence_summary
    assert report.suggested_sheet_fields["错误原因"].startswith("评测资产问题")
    assert report.recommended_actions == [
        {
            "category": "evaluation_asset",
            "priority": "high",
            "status": "pending",
            "summary": "补齐评分标准。",
            "detail": "补充 exact match、可接受别字/格式、box_id 对齐等评分规则，避免 0/1 结论不可审计。",
            "evidence_ids": "e-asset-diagnostic",
            "artifact_ids": "",
            "trace_refs": "",
        }
    ]
    assert report.evaluation_asset_diagnostics == [
        {
            "source": "prompt",
            "status": "pass",
            "severity": "info",
            "summary": "Prompt 已要求结构化 JSON 输出。",
            "recommendation": "保持 prompt 中明确的输出 schema、证据引用和约束条件。",
            "evidence_ids": "e-asset-diagnostic",
            "artifact_ids": "",
            "trace_refs": "",
        },
        {
            "source": "golden_answer",
            "status": "pass",
            "severity": "info",
            "summary": "标答包含 1 个 answer 项。",
            "recommendation": "继续确保 golden answer 覆盖关键目标、区域或结构化字段。",
            "evidence_ids": "e-asset-diagnostic",
            "artifact_ids": "",
            "trace_refs": "",
        },
        {
            "source": "scoring_standard",
            "status": "fail",
            "severity": "high",
            "summary": "评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
            "recommendation": "补充 exact match、可接受别字/格式、box_id 对齐等评分规则。",
            "evidence_ids": "e-asset-diagnostic",
            "artifact_ids": "",
            "trace_refs": "",
        },
    ]


def test_generate_report_flags_empty_golden_answer_as_evaluation_asset_issue() -> None:
    case = _diagnostic_case(golden_answer={"answers": []})
    plan = plan_experiments(case)
    run_result = _one_failed_answer_mismatch_result(case)

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "evaluation_asset_issue"
    assert report.root_cause.label == "golden_answer_issue"
    assert report.root_cause.confidence == "high"
    assert "标答为空" in report.root_cause.evidence_summary


def test_generate_report_flags_prompt_schema_issue_when_parse_errors_repeat() -> None:
    case = _diagnostic_case(prompt="请识别图片中的学生答案。")
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-parse-error",
                step_name="baseline_replay",
                trial=0,
                response_parse_error="Expecting value: line 1 column 1",
                raw_output="答案是42",
                judge=JudgeResult(score=0, reasons=["response_parse_error"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "evaluation_asset_issue"
    assert report.root_cause.label == "prompt_schema_issue"
    assert report.root_cause.confidence == "medium"
    assert "prompt 未明确 JSON" in report.root_cause.evidence_summary
    assert {
        "source": "prompt",
        "status": "warn",
        "severity": "medium",
        "summary": "Prompt 未明确要求 JSON/schema，且 evidence 出现解析失败。",
        "recommendation": "要求模型只输出可解析 JSON，并声明关键字段、类型和禁止额外文本。",
        "evidence_ids": "e-parse-error",
        "artifact_ids": "",
        "trace_refs": "",
    } in report.evaluation_asset_diagnostics


def _diagnostic_case(
    *,
    prompt: str = "Return JSON with answers.",
    scoring_standard: str = "box_id and student_answer must match exactly.",
    golden_answer: dict[str, object] | None = None,
) -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "diagnostic-case",
            "image_uri": "file:///tmp/diagnostic.png",
            "prompt": prompt,
            "golden_answer": golden_answer or {"answers": [{"box_id": 1, "student_answer": "42"}]},
            "scoring_standard": scoring_standard,
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"24\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )


def _one_failed_answer_mismatch_result(case: DebugCase) -> ExperimentRunResult:
    return ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-asset-diagnostic",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["box 1 student_answer_mismatch"],
                    scoring_standard=case.scoring_standard,
                    affected_box_ids=[1],
                    deltas=[
                        {
                            "target_id": "box:1",
                            "expected": "42",
                            "actual": "24",
                            "reason": "student_answer_mismatch",
                            "metadata": {
                                "box_id": 1,
                                "field": "student_answer",
                                "legacy_reason": "student_answer_mismatch",
                            },
                        }
                    ],
                ),
            )
        ],
    )

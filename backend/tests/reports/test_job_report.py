from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_build_report_for_job_reconstructs_experiment_summary_from_persisted_evidence() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "job-report-case-1"})
    repository.save_case(case)
    repository.create_job(job_id="job-1", case_id=case.case_id, baseline_trials=5)
    repository.save_evidence(
        job_id="job-1",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-report-case-1:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="job-report-case-1:baseline:1",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            ),
        ],
    )

    report = build_report_for_job(repository, "job-1")

    assert report is not None
    assert report.job_id == "job-1"
    assert report.case_id == case.case_id
    assert report.experiment_summary is not None
    assert report.experiment_summary.total_trials == 2
    assert report.experiment_summary.success_count == 1
    assert report.experiment_summary.failed_trial_count == 1
    assert report.experiment_summary.stability_label == "unstable"
    assert report.experiment_summary.evidence_ids == [
        "job-report-case-1:baseline:0",
        "job-report-case-1:baseline:1",
    ]


def test_build_report_for_job_returns_none_for_missing_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    report = build_report_for_job(repository, "missing-job")

    assert report is None


def test_build_report_for_job_merges_recommended_action_statuses() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "status-merge-case",
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
    repository.save_case(case)
    repository.create_job(job_id="job-status-merge", case_id=case.case_id)
    repository.save_evidence(
        job_id="job-status-merge",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-image-only",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id="e-text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    repository.save_recommended_action_status(
        job_id="job-status-merge",
        action_index=0,
        status="accepted",
        actor="qa-reviewer",
        note="approved prompt update",
    )
    repository.save_recommended_action_status(
        job_id="job-status-merge",
        action_index=2,
        status="applied",
        actor="qa-reviewer",
        note="model capability ticket linked",
    )

    report = build_report_for_job(repository, "job-status-merge")

    assert report is not None
    assert [action["status"] for action in report.recommended_actions] == [
        "accepted",
        "pending",
        "applied",
    ]


def test_build_report_for_job_includes_recommended_action_verification_results() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "job-report-verification-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=2)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id="job-source:baseline:1",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    repository.create_job(job_id="job-verification", case_id=case.case_id, baseline_trials=2)
    repository.save_evidence(
        job_id="job-verification",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-verification:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="job-verification:baseline:1",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    repository.mark_completed("job-verification")
    repository.save_recommended_action_verification(
        job_id="job-source",
        action_index=0,
        verification_job_id="job-verification",
        actor="qa-reviewer",
        note="verify prompt fix",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert report.verification_results[0]["action_index"] == 0
    assert report.verification_results[0]["verification_job_id"] == "job-verification"
    assert report.verification_results[0]["result"] == "resolved"
    assert report.verification_results[0]["source_success_rate"] == 0.5
    assert report.verification_results[0]["verification_success_rate"] == 1.0
    assert report.verification_results[0]["summary"] == "验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。"


def test_build_report_for_job_includes_strategy_follow_up_results() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "job-report-strategy-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-strategy-follow-up", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-strategy-follow-up",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-strategy-follow-up:strategy-pass",
                step_name="strategy_evidence_audit_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    repository.mark_completed("job-strategy-follow-up")
    repository.save_strategy_follow_up_job(
        source_job_id="job-source",
        stage="evidence_audit",
        planned_steps="strategy_evidence_audit_probe",
        follow_up_job_id="job-strategy-follow-up",
        actor="strategy-operator",
        note="audit evidence chain",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert report.strategy_follow_up_results == [
        {
            "source_job_id": "job-source",
            "stage": "evidence_audit",
            "planned_steps": "strategy_evidence_audit_probe",
            "follow_up_job_id": "job-strategy-follow-up",
            "actor": "strategy-operator",
            "note": "audit evidence chain",
            "created_at": report.strategy_follow_up_results[0]["created_at"],
            "outcome": "passed_stop_condition",
            "success_rate": 1.0,
            "summary": "Strategy follow-up job passed all probes; stop condition is likely satisfied.",
            "escalation": "",
        }
    ]


def test_build_report_for_job_includes_targeted_probe_results() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "job-report-targeted-case",
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
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:cross-modal",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-targeted-probe", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-targeted-probe",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-targeted-probe:still-fail",
                step_name="targeted_multimodal_conflict_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-targeted-probe")
    repository.save_targeted_probe_job(
        source_job_id="job-source",
        target_id="multimodal:conflict:1",
        planned_steps="targeted_multimodal_conflict_probe",
        probe_job_id="job-targeted-probe",
        actor="targeted-operator",
        note="probe conflict target",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert report.targeted_probe_results == [
        {
            "source_job_id": "job-source",
            "source": "targeted_probe",
            "target_id": "multimodal:conflict:1",
            "planned_steps": "targeted_multimodal_conflict_probe",
            "probe_job_id": "job-targeted-probe",
            "parent_probe_job_id": "",
            "trigger_outcome": "",
            "actor": "targeted-operator",
            "note": "probe conflict target",
            "created_at": report.targeted_probe_results[0]["created_at"],
            "outcome": "target_still_failing",
            "success_rate": 0.0,
            "summary": "Targeted probe still failed on multimodal:conflict:1; escalation is recommended.",
            "escalation": "Run deeper localized replay or modality-specific probes for multimodal:conflict:1.",
        }
    ]


def test_build_report_for_job_adds_escalation_follow_up_for_failed_targeted_probe() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "job-report-targeted-escalation-case",
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
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:cross-modal",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-targeted-probe", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-targeted-probe",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-targeted-probe:still-fail",
                step_name="targeted_multimodal_conflict_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-targeted-probe")
    repository.save_targeted_probe_job(
        source_job_id="job-source",
        target_id="multimodal:conflict:1",
        planned_steps="targeted_multimodal_conflict_probe",
        probe_job_id="job-targeted-probe",
        actor="targeted-operator",
        note="probe conflict target",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert report.targeted_probe_results[0]["outcome"] == "target_still_failing"
    assert {
        "source": "targeted_probe_outcome",
        "target_id": "multimodal:conflict:1",
        "result": "target_still_failing",
        "parent_probe_job_id": "job-targeted-probe",
        "planned_steps": "targeted_escalation_multimodal_conflict_probe",
        "summary": (
            "Targeted probe job job-targeted-probe for multimodal:conflict:1 未满足停止条件，"
            "已生成升级 probing：targeted_escalation_multimodal_conflict_probe。"
        ),
    } in report.follow_up_experiments


def test_build_report_for_job_stops_targeted_escalation_at_max_depth() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "job-report-targeted-guardrail-case",
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
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:cross-modal",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    parent_probe_job_id = ""
    for index in range(3):
        probe_job_id = f"job-targeted-probe-{index + 1}"
        repository.create_job(job_id=probe_job_id, case_id=case.case_id, baseline_trials=1)
        repository.save_evidence(
            job_id=probe_job_id,
            case_id=case.case_id,
            evidence=[
                ExperimentEvidence(
                    evidence_id=f"{probe_job_id}:still-fail",
                    step_name="targeted_multimodal_conflict_probe",
                    trial=0,
                    raw_output=case.predictions[0].raw_output,
                    judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
                )
            ],
        )
        repository.mark_completed(probe_job_id)
        repository.save_targeted_probe_job(
            source_job_id="job-source",
            target_id="multimodal:conflict:1",
            planned_steps="targeted_multimodal_conflict_probe",
            probe_job_id=probe_job_id,
            source="targeted_probe" if index == 0 else "targeted_probe_outcome",
            parent_probe_job_id=parent_probe_job_id,
            trigger_outcome="" if index == 0 else "target_still_failing",
            actor="targeted-operator",
            note=f"probe round {index + 1}",
        )
        parent_probe_job_id = probe_job_id
    repository.save_human_handoff_status(
        job_id="job-source",
        target_id="multimodal:conflict:1",
        status="resolved",
        actor="human-debugger",
        note="Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
    )
    repository.create_job(job_id="job-final-attribution-verify", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-final-attribution-verify",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-final-attribution-verify:pass",
                step_name="final_attribution_prompt_verification",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    repository.mark_completed("job-final-attribution-verify")
    repository.save_strategy_follow_up_job(
        source_job_id="job-source",
        stage="final_attribution:multimodal:conflict:1",
        planned_steps="final_attribution_prompt_verification",
        follow_up_job_id="job-final-attribution-verify",
        actor="final-attribution-operator",
        note="verify final prompt attribution",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert not any(
        follow_up.get("source") == "targeted_probe_outcome"
        and follow_up.get("target_id") == "multimodal:conflict:1"
        for follow_up in report.follow_up_experiments
    )
    assert {
        "source": "targeted_probe_guardrail",
        "target_id": "multimodal:conflict:1",
        "result": "target_still_failing",
        "planned_steps": "",
        "summary": (
            "Targeted probe chain for multimodal:conflict:1 reached max depth 3; "
            "stop automatic escalation and require human review."
        ),
        "stop_condition": "max_targeted_probe_depth_reached",
    } in report.follow_up_experiments
    assert report.human_handoff_requests == [
        {
            "source": "targeted_probe_guardrail",
            "target_id": "multimodal:conflict:1",
            "priority": "high",
            "reason": "max_targeted_probe_depth_reached",
            "summary": "Targeted probe chain for multimodal:conflict:1 reached max depth 3.",
            "recommended_owner": "human-debugger",
            "next_action": "Review the full targeted probe chain, inspect evidence artifacts, and decide whether to update prompt, evaluation assets, or model capability attribution.",
        }
    ]
    assert report.human_handoff_statuses == [
        {
            "job_id": "job-source",
            "target_id": "multimodal:conflict:1",
            "status": "resolved",
            "actor": "human-debugger",
            "note": "Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
            "created_at": report.human_handoff_statuses[0]["created_at"],
            "updated_at": report.human_handoff_statuses[0]["updated_at"],
        }
    ]
    assert report.final_attributions == [
        {
            "source": "human_handoff",
            "target_id": "multimodal:conflict:1",
            "category": "prompt_issue",
            "status": "resolved",
            "actor": "human-debugger",
            "summary": "Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
            "recommended_action": "Update prompt instructions and rerun verification before assigning model capability blame.",
        }
    ]
    assert {
        "category": "prompt_patch",
        "priority": "high",
        "status": "pending",
        "summary": "Apply final attribution fix for multimodal:conflict:1.",
        "detail": "Update prompt instructions and rerun verification before assigning model capability blame.",
    } in report.recommended_actions
    assert {
        "source": "final_attribution",
        "target_id": "multimodal:conflict:1",
        "category": "prompt_issue",
        "planned_steps": "final_attribution_prompt_verification",
        "summary": (
            "Final attribution for multimodal:conflict:1 is prompt_issue; "
            "run final_attribution_prompt_verification to verify the recommended fix."
        ),
    } in report.follow_up_experiments
    assert report.final_attribution_verification_results == [
        {
            "source": "final_attribution",
            "target_id": "multimodal:conflict:1",
            "category": "prompt_issue",
            "verification_job_id": "job-final-attribution-verify",
            "result": "resolved",
            "success_rate": 1.0,
            "summary": "Final attribution verification for multimodal:conflict:1 resolved the issue.",
        }
    ]


def test_build_report_for_job_recovers_unresolved_final_attribution_verification() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "job-report-attribution-recovery-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-attribution-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-attribution-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-attribution-source:baseline",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["image:region:1 still failing"]),
            )
        ],
    )
    repository.save_human_handoff_status(
        job_id="job-attribution-source",
        target_id="image:region:1",
        status="resolved",
        actor="human-debugger",
        note="Final attribution: prompt needs stricter region reading instructions.",
    )
    repository.create_job(job_id="job-final-attribution-recovery-verify", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-final-attribution-recovery-verify",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-final-attribution-recovery-verify:fail",
                step_name="final_attribution_prompt_verification",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["image:region:1 still failing"]),
            )
        ],
    )
    repository.mark_completed("job-final-attribution-recovery-verify")
    repository.save_strategy_follow_up_job(
        source_job_id="job-attribution-source",
        stage="final_attribution:image:region:1",
        planned_steps="final_attribution_prompt_verification",
        follow_up_job_id="job-final-attribution-recovery-verify",
        actor="final-attribution-operator",
        note="verification still fails",
    )

    report = build_report_for_job(repository, "job-attribution-source")

    assert report is not None
    assert {
        "category": "attribution_recovery",
        "priority": "critical",
        "status": "pending",
        "summary": "Recover unresolved final attribution verification for image:region:1.",
        "detail": (
            "Final attribution verification job job-final-attribution-recovery-verify returned not_resolved. "
            "Re-open the attribution, inspect verification evidence, and run final_attribution_recovery_probe."
        ),
    } in report.recommended_actions
    assert {
        "source": "final_attribution_verification_outcome",
        "target_id": "image:region:1",
        "category": "prompt_issue",
        "result": "not_resolved",
        "verification_job_id": "job-final-attribution-recovery-verify",
        "planned_steps": "final_attribution_recovery_probe",
        "summary": (
            "Final attribution verification for image:region:1 is not_resolved; "
            "run final_attribution_recovery_probe to reassess the root cause before closure."
        ),
    } in report.follow_up_experiments


def test_build_report_for_job_closes_successful_final_attribution_recovery() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "job-report-attribution-closure-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-attribution-closure-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-attribution-closure-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-attribution-closure-source:baseline",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["image:region:1 still failing"]),
            )
        ],
    )
    repository.save_human_handoff_status(
        job_id="job-attribution-closure-source",
        target_id="image:region:1",
        status="resolved",
        actor="human-debugger",
        note="Final attribution: prompt needs stricter region reading instructions.",
    )
    repository.create_job(job_id="job-final-attribution-verify-fail", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-final-attribution-verify-fail",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-final-attribution-verify-fail:fail",
                step_name="final_attribution_prompt_verification",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["image:region:1 still failing"]),
            )
        ],
    )
    repository.mark_completed("job-final-attribution-verify-fail")
    repository.save_strategy_follow_up_job(
        source_job_id="job-attribution-closure-source",
        stage="final_attribution:image:region:1",
        planned_steps="final_attribution_prompt_verification",
        follow_up_job_id="job-final-attribution-verify-fail",
        actor="final-attribution-operator",
        note="verification still fails",
    )
    repository.create_job(job_id="job-final-attribution-recovery-pass", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-final-attribution-recovery-pass",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-final-attribution-recovery-pass:pass",
                step_name="final_attribution_recovery_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    repository.mark_completed("job-final-attribution-recovery-pass")
    repository.save_strategy_follow_up_job(
        source_job_id="job-attribution-closure-source",
        stage="final_attribution_recovery:image:region:1",
        planned_steps="final_attribution_recovery_probe",
        follow_up_job_id="job-final-attribution-recovery-pass",
        actor="recovery-operator",
        note="recovery resolved attribution",
    )

    report = build_report_for_job(repository, "job-attribution-closure-source")

    assert report is not None
    assert report.final_attribution_recovery_results == [
        {
            "source": "final_attribution_recovery",
            "target_id": "image:region:1",
            "category": "prompt_issue",
            "recovery_job_id": "job-final-attribution-recovery-pass",
            "result": "closed",
            "success_rate": 1.0,
            "summary": "Final attribution recovery for image:region:1 closed the attribution loop.",
        }
    ]
    assert {
        "category": "attribution_closure",
        "priority": "high",
        "status": "pending",
        "summary": "Close final attribution recovery for image:region:1.",
        "detail": (
            "Recovery job job-final-attribution-recovery-pass closed the attribution loop. "
            "Record closure and keep the resolved case in regression monitoring."
        ),
    } in report.recommended_actions


def test_build_report_for_job_adds_escalation_follow_up_for_failed_strategy_outcome() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "job-report-strategy-escalation-case",
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
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-source:cross-modal",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-strategy-follow-up", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-strategy-follow-up",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-strategy-follow-up:still-fail",
                step_name="strategy_ablation_expansion_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-strategy-follow-up")
    repository.save_strategy_follow_up_job(
        source_job_id="job-source",
        stage="ablation_expansion",
        planned_steps="strategy_ablation_expansion_probe",
        follow_up_job_id="job-strategy-follow-up",
        actor="strategy-operator",
        note="expand ablation",
    )

    report = build_report_for_job(repository, "job-source")

    assert report is not None
    assert report.strategy_follow_up_results[0]["outcome"] == "needs_escalation"
    assert {
        "source": "strategy_outcome",
        "stage": "ablation_expansion",
        "result": "needs_escalation",
        "planned_steps": "strategy_escalation_single_modality_probe",
        "summary": (
            "策略阶段 ablation_expansion 的 follow-up job job-strategy-follow-up 未满足停止条件，"
            "已生成升级 probing：strategy_escalation_single_modality_probe。"
        ),
    } in report.follow_up_experiments

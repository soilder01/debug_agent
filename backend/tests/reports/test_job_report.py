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

from debug_agent.cases.fixtures import load_fixture_case
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

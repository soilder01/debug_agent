import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from debug_agent.api import routes
from debug_agent.api.routes import job_repository
from debug_agent.artifacts.images import EvidenceArtifact
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app
from debug_agent.storage.models import (
    DebugCaseRow,
    DebugJobAttemptRow,
    DebugJobRow,
    DebugRunStageRow,
    EvidenceRow,
    SpreadsheetWritebackAuditRow,
)
from debug_agent.telemetry.performance import performance_recorder, record_performance_event


def _delete_job(job_id: str) -> None:
    with routes.engine.begin() as connection:
        connection.execute(delete(EvidenceRow).where(EvidenceRow.job_id == job_id))
        connection.execute(delete(DebugRunStageRow).where(DebugRunStageRow.job_id == job_id))
        connection.execute(delete(DebugJobAttemptRow).where(DebugJobAttemptRow.job_id == job_id))
        connection.execute(delete(SpreadsheetWritebackAuditRow).where(SpreadsheetWritebackAuditRow.job_id == job_id))
        connection.execute(delete(DebugJobRow).where(DebugJobRow.job_id == job_id))


def _delete_case(case_id: str) -> None:
    with routes.engine.begin() as connection:
        connection.execute(delete(DebugCaseRow).where(DebugCaseRow.case_id == case_id))


def test_export_debug_jobs_zip_contains_summary_and_job_payloads() -> None:
    client = TestClient(app)
    submitted = client.post("/cases/handwrite233/debug-jobs").json()
    performance_recorder.clear()
    try:
        record_performance_event(component="api", operation="GET /jobs/{job_id}/report", duration_ms=25)
        job_repository.save_spreadsheet_writeback_audit(
            job_id=submitted["job_id"],
            status="succeeded",
            row_id="7",
            report_url=f"https://debug-agent.local/jobs/{submitted['job_id']}/report",
            fields={"错误原因": "模型无法稳定识别涂改后的最终答案。"},
            error_message="",
        )

        response = client.get(f"/exports/debug-jobs.zip?job_ids={submitted['job_id']}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = set(archive.namelist())
        safe_job_id = submitted["job_id"]
        assert "manifest.json" in names
        assert "summary.csv" in names
        assert "performance_summary.json" in names
        assert f"jobs/{safe_job_id}.json" in names
        assert f"html_reports/{safe_job_id}.html" in names
        assert f"run_stages/{safe_job_id}.json" in names
        assert f"evidence/{safe_job_id}.json" in names
        assert f"evidence_ledgers/{safe_job_id}.json" in names
        assert f"writeback_audits/{safe_job_id}.json" in names
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["job_ids"] == [submitted["job_id"]]
        assert "performance_summary.json" in manifest["contents"]
        assert "artifacts/*" in manifest["contents"]
        performance = json.loads(archive.read("performance_summary.json").decode("utf-8"))
        assert performance["total_count"] >= 1
        assert any(item["component"] == "api" for item in performance["aggregates"])
        summary = archive.read("summary.csv").decode("utf-8-sig")
        assert submitted["job_id"] in summary
        assert "succeeded" in summary
        job_payload = json.loads(archive.read(f"jobs/{safe_job_id}.json").decode("utf-8"))
        assert job_payload["case_id"] == "handwrite233"
        html = archive.read(f"html_reports/{safe_job_id}.html").decode("utf-8")
        assert "Debug Report" in html
        assert submitted["job_id"] in html
    finally:
        performance_recorder.clear()
        _delete_job(submitted["job_id"])


def test_export_debug_jobs_supports_frontend_api_prefix() -> None:
    client = TestClient(app)
    submitted = client.post("/cases/handwrite233/debug-jobs").json()

    try:
        response = client.get(f"/api/exports/debug-jobs.zip?job_ids={submitted['job_id']}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
    finally:
        _delete_job(submitted["job_id"])


def test_export_debug_jobs_zip_includes_materialized_artifact_files() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        artifact_dir = temp_path / "artifacts"
        artifact_dir.mkdir()
        artifact_path = artifact_dir / "JSZN-131_baseline_replay_0_input-snapshot.mp4"
        artifact_path.write_bytes(b"fake-video")
        original_artifact_dir = routes.settings.image_artifact_dir
        routes.settings.image_artifact_dir = artifact_dir
        job_id = f"artifact-export-{uuid4()}"
        try:
            job_repository.create_job(job_id, "JSZN-131", baseline_trials=1)
            job_repository.save_evidence(
                job_id=job_id,
                case_id="JSZN-131",
                evidence=[
                    ExperimentEvidence(
                        evidence_id="JSZN-131:baseline_replay:0",
                        step_name="baseline_replay",
                        trial=0,
                        raw_output="{}",
                        judge=JudgeResult(score=0, reasons=["failed"]),
                        artifacts=[
                            EvidenceArtifact(
                                artifact_id="JSZN-131:baseline_replay:0:input-snapshot",
                                kind="input_snapshot",
                                artifact_type="request",
                                derived_uri=artifact_path.resolve().as_uri(),
                            )
                        ],
                    )
                ],
            )
            job_repository.mark_completed(job_id)
            client = TestClient(app)

            response = client.get(f"/exports/debug-jobs.zip?job_ids={job_id}")

            assert response.status_code == 200
            archive = zipfile.ZipFile(io.BytesIO(response.content))
            assert archive.read(
                f"artifacts/{job_id}/JSZN-131_baseline_replay_0_input-snapshot.mp4"
            ) == b"fake-video"
        finally:
            routes.settings.image_artifact_dir = original_artifact_dir
            _delete_job(job_id)


def test_export_debug_jobs_html_report_handles_dict_report_items() -> None:
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": f"export-dict-report-{uuid4()}"})
    job_id = f"dict-report-export-{uuid4()}"
    job_repository.save_case(case)
    job_repository.create_job(job_id, case.case_id, baseline_trials=1)
    job_repository.save_evidence(
        job_id=job_id,
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{case.case_id}:baseline_replay:0",
                step_name="baseline_replay",
                trial=0,
                raw_output='{"answers":[{"box_id":1,"student_answer":"wrong"}]}',
                judge=JudgeResult(
                    score=0,
                    reasons=["student_answer_mismatch"],
                    deltas=[
                        {
                            "target_id": "box:1",
                            "expected": "ok",
                            "actual": "wrong",
                            "reason": "student_answer_mismatch",
                            "metadata": {"box_id": 1},
                        }
                    ],
                ),
            )
        ],
    )
    job_repository.mark_completed(job_id)
    client = TestClient(app)

    response = client.get(f"/exports/debug-jobs.zip?job_ids={job_id}")

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    html = archive.read(f"html_reports/{job_id}.html").decode("utf-8")
    assert f"{case.case_id}:baseline_replay:0" in html
    assert "student_answer_mismatch" in html
    _delete_job(job_id)
    _delete_case(case.case_id)


def test_export_debug_jobs_returns_empty_archive_for_empty_status_filter() -> None:
    client = TestClient(app)

    response = client.get("/exports/debug-jobs.zip?status=never-used-status")

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["job_count"] == 0
    assert archive.read("summary.csv").decode("utf-8-sig").startswith("job_id,case_id,status")

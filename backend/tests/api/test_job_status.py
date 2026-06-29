from fastapi.testclient import TestClient

from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_debug_case_returns_queryable_completed_job_status() -> None:
    client = TestClient(app)

    debug_response = client.post("/cases/handwrite233/debug")

    assert debug_response.status_code == 200
    job_id = debug_response.json()["job_id"]
    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["case_id"] == "handwrite233"
    assert body["status"] == "completed"
    assert body["attempt_count"] == 1
    assert body["max_attempts"] == 2
    assert body["remaining_attempts"] == 1
    assert body["will_retry"] is False
    assert body["retry_recommendation"] == "no_retry_needed"
    assert body["retry_recommendation_detail"] == {
        "code": "no_retry_needed",
        "label": "无需重试",
        "action": "任务已完成，直接查看证据链和结论。",
        "severity": "info",
    }
    assert body["error_message"] is None
    assert len(body["evidence_ids"]) == 6
    assert body["evidence_error_counts"] == {
        "total_evidence": 6,
        "failed_judgements": 6,
        "response_parse_errors": 0,
        "model_call_errors": 0,
    }
    assert body["spreadsheet_writeback_audit"] is None


def test_job_status_includes_spreadsheet_writeback_audit_summary() -> None:
    client = TestClient(app)
    from debug_agent.api.routes import job_repository

    job_repository.create_job(job_id="job-status-writeback-audit", case_id="case-1")
    job_repository.save_spreadsheet_writeback_audit(
        job_id="job-status-writeback-audit",
        status="failed",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-status-writeback-audit/report",
        fields={},
        error_message="permission denied",
    )

    response = client.get("/jobs/job-status-writeback-audit")

    assert response.status_code == 200
    assert response.json()["spreadsheet_writeback_audit"] == {
        "status": "failed",
        "row_id": "7",
        "report_url": "https://debug-agent.local/jobs/job-status-writeback-audit/report",
        "error_message": "permission denied",
        "updated_at": response.json()["spreadsheet_writeback_audit"]["updated_at"],
    }
    assert response.json()["spreadsheet_writeback_audit"]["updated_at"]
    job_repository.mark_failed("job-status-writeback-audit", "test cleanup")


def test_requeued_failed_job_status_exposes_retry_budget() -> None:
    client = TestClient(app)
    from debug_agent.api.routes import job_repository

    job_repository.create_job(job_id="retry-status-job", case_id="missing-case")
    claimed = job_repository.claim_next_created_job()
    assert claimed is not None
    job_repository.release_for_retry("retry-status-job", "Fixture case not found: missing-case")

    response = client.get("/jobs/retry-status-job")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "created"
    assert body["attempt_count"] == 1
    assert body["max_attempts"] == 2
    assert body["remaining_attempts"] == 1
    assert body["will_retry"] is True
    assert body["retry_recommendation"] == "retry_waiting_for_next_attempt"


def test_job_status_recommends_retry_for_model_call_errors_with_budget() -> None:
    client = TestClient(app)
    from debug_agent.api.routes import job_repository

    job_repository.create_job(job_id="000-model-error-retry-job", case_id="case-1")
    claimed = job_repository.claim_next_created_job()
    assert claimed is not None
    assert claimed.job_id == "000-model-error-retry-job"
    job_repository.release_for_retry("000-model-error-retry-job", "model request timed out")
    job_repository.save_evidence(
        job_id="000-model-error-retry-job",
        case_id="case-1",
        evidence=[
            ExperimentEvidence(
                evidence_id="case-1:model:0",
                step_name="model",
                trial=0,
                model_call_error_type="TimeoutError",
                model_call_error_message="model request timed out",
                raw_output="",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            )
        ],
    )

    response = client.get("/jobs/000-model-error-retry-job")

    assert response.status_code == 200
    assert response.json()["retry_recommendation"] == "retry_model_call_error"
    job_repository.mark_failed("000-model-error-retry-job", "test cleanup")


def test_job_status_does_not_recommend_retry_for_parse_errors() -> None:
    client = TestClient(app)
    from debug_agent.api.routes import job_repository

    job_repository.create_job(job_id="000-parse-error-no-retry-job", case_id="case-1")
    job_repository.save_evidence(
        job_id="000-parse-error-no-retry-job",
        case_id="case-1",
        evidence=[
            ExperimentEvidence(
                evidence_id="case-1:parse:0",
                step_name="parse",
                trial=0,
                response_parse_error="Expecting value",
                raw_output="not-json",
                judge=JudgeResult(score=0, reasons=["response_parse_error"]),
            )
        ],
    )

    response = client.get("/jobs/000-parse-error-no-retry-job")

    assert response.status_code == 200
    assert response.json()["retry_recommendation"] == "inspect_parse_error"
    job_repository.mark_failed("000-parse-error-no-retry-job", "test cleanup")

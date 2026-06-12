from fastapi.testclient import TestClient

from debug_agent.api.routes import job_repository
from debug_agent.main import app


def test_job_listing_returns_submitted_jobs_with_retry_metadata() -> None:
    client = TestClient(app)

    first = client.post("/cases/handwrite233/debug-jobs").json()
    second = client.post("/cases/handwrite233/debug-jobs").json()

    response = client.get("/jobs")

    assert response.status_code == 200
    jobs_by_id = {job["job_id"]: job for job in response.json()["jobs"]}
    for submitted in (first, second):
        job = jobs_by_id[submitted["job_id"]]
        assert job["case_id"] == "handwrite233"
        assert job["status"] == "created"
        assert job["created_at"] != ""
        assert job["updated_at"] != ""
        assert job["max_attempts"] == 2
        assert job["remaining_attempts"] == 2
        assert job["will_retry"] is False
        assert job["retry_recommendation"] == "retry_budget_exhausted"
        assert job["retry_recommendation_detail"]["label"] == "重试预算已耗尽"
        assert job["evidence_error_counts"] == {
            "total_evidence": 0,
            "failed_judgements": 0,
            "response_parse_errors": 0,
            "model_call_errors": 0,
        }
        assert job["spreadsheet_writeback_audit"] is None
        job_repository.mark_failed(submitted["job_id"], "test cleanup")


def test_job_listing_includes_spreadsheet_writeback_audit_summary() -> None:
    client = TestClient(app)
    submitted = client.post("/cases/handwrite233/debug-jobs").json()
    job_repository.save_spreadsheet_writeback_audit(
        job_id=submitted["job_id"],
        status="succeeded",
        row_id="9",
        report_url=f"https://debug-agent.local/jobs/{submitted['job_id']}/report",
        fields={"错误原因": "模型无法稳定识别涂改后的最终答案。"},
        error_message="",
    )

    response = client.get("/jobs")

    assert response.status_code == 200
    job = {item["job_id"]: item for item in response.json()["jobs"]}[submitted["job_id"]]
    assert job["spreadsheet_writeback_audit"]["status"] == "succeeded"
    assert job["spreadsheet_writeback_audit"]["row_id"] == "9"
    assert job["spreadsheet_writeback_audit"]["error_message"] == ""
    assert job["spreadsheet_writeback_audit"]["updated_at"]
    job_repository.mark_failed(submitted["job_id"], "test cleanup")


def test_job_listing_filters_jobs_by_status() -> None:
    client = TestClient(app)

    failed = client.post("/cases/handwrite233/debug-jobs").json()
    created = client.post("/cases/handwrite233/debug-jobs").json()
    job_repository.mark_failed(failed["job_id"], "forced failure for filter test")

    response = client.get("/jobs?status=failed")

    assert response.status_code == 200
    job_ids = [job["job_id"] for job in response.json()["jobs"]]
    assert failed["job_id"] in job_ids
    assert created["job_id"] not in job_ids
    job_repository.mark_failed(created["job_id"], "test cleanup")


def test_job_listing_limits_number_of_returned_jobs() -> None:
    client = TestClient(app)

    submitted_jobs = [client.post("/cases/handwrite233/debug-jobs").json() for _ in range(3)]

    response = client.get("/jobs?limit=2")

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 2
    assert body["total_count"] >= 3
    assert body["total_count"] > len(body["jobs"])
    for submitted in submitted_jobs:
        job_repository.mark_failed(submitted["job_id"], "test cleanup")


def test_job_listing_offsets_returned_jobs_without_changing_total_count() -> None:
    client = TestClient(app)

    submitted_jobs = [client.post("/cases/handwrite233/debug-jobs").json() for _ in range(2)]

    first_page_response = client.get("/jobs?limit=2")
    second_page_response = client.get("/jobs?offset=1&limit=1")

    assert first_page_response.status_code == 200
    assert second_page_response.status_code == 200
    first_page = first_page_response.json()
    second_page = second_page_response.json()
    assert len(first_page["jobs"]) == 2
    assert len(second_page["jobs"]) == 1
    assert second_page["jobs"][0]["job_id"] == first_page["jobs"][1]["job_id"]
    assert second_page["total_count"] == first_page["total_count"]
    for submitted in submitted_jobs:
        job_repository.mark_failed(submitted["job_id"], "test cleanup")


def test_job_listing_can_sort_newest_jobs_first() -> None:
    client = TestClient(app)

    submitted_jobs = [client.post("/cases/handwrite233/debug-jobs").json() for _ in range(2)]

    response = client.get("/jobs?sort=created_at_desc&limit=2")

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 2
    created_at_values = [job["created_at"] for job in body["jobs"]]
    assert created_at_values == sorted(created_at_values, reverse=True)
    for submitted in submitted_jobs:
        job_repository.mark_failed(submitted["job_id"], "test cleanup")


def test_job_listing_rejects_unknown_sort_value() -> None:
    client = TestClient(app)

    response = client.get("/jobs?sort=unknown")

    assert response.status_code == 422

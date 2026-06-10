from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.main import app


def test_jsonl_import_persists_cases_and_creates_jobs() -> None:
    client = TestClient(app)
    case_json = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-jsonl-1"}).model_dump_json()

    response = client.post("/imports/jsonl", json={"jsonl": case_json, "create_jobs": True})

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["imported-jsonl-1"]
    assert body["rejected_lines"] == []
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "imported-jsonl-1"

    job_id = body["jobs"][0]["job_id"]
    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "created"

    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    assert client.get(f"/jobs/{job_id}").json()["status"] == "completed"

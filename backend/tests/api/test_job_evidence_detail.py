from fastapi.testclient import TestClient

from debug_agent.main import app


def test_job_evidence_detail_returns_persisted_model_metadata() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true")
    submitted = submit_response.json()
    job_response = client.get(f"/jobs/{submitted['job_id']}")
    evidence_id = job_response.json()["evidence_ids"][0]

    response = client.get(f"/jobs/{submitted['job_id']}/evidence/{evidence_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_id"] == evidence_id
    assert body["step_name"] == "baseline_replay"
    assert body["model_name"] == "fake"
    assert body["model_provider"] == "fake"
    assert body["model_id"] == "fake"
    assert body["judge"]["score"] == 0


def test_job_evidence_detail_returns_404_for_unknown_evidence() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true")
    submitted = submit_response.json()

    response = client.get(f"/jobs/{submitted['job_id']}/evidence/missing")

    assert response.status_code == 404

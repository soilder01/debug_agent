from fastapi.testclient import TestClient

from debug_agent.main import app


def test_evidence_detail_returns_stored_replay_evidence() -> None:
    client = TestClient(app)
    debug_response = client.post("/cases/handwrite233/debug")
    evidence_id = debug_response.json()["experiment_summary"]["evidence_ids"][0]

    response = client.get(f"/cases/handwrite233/evidence/{evidence_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_id"] == evidence_id
    assert body["step_name"] == "baseline_replay"
    assert body["judge"]["score"] == 0

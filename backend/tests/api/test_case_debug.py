from fastapi.testclient import TestClient

from debug_agent.main import app


def test_debug_fixture_case_returns_report() -> None:
    client = TestClient(app)

    response = client.post("/cases/handwrite233/debug")

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "handwrite233"
    assert body["status"] == "needs_human_review"
    assert "baseline_replay" in body["planned_experiments"]

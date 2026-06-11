from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.main import app


def test_case_detail_returns_imported_case() -> None:
    client = TestClient(app)
    imported_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "case-detail-imported-1"})

    import_response = client.post(
        "/imports/jsonl",
        json={"jsonl": imported_case.model_dump_json(), "create_jobs": False},
    )
    response = client.get("/cases/case-detail-imported-1")

    assert import_response.status_code == 202
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "case-detail-imported-1"
    assert body["prompt"] == imported_case.prompt
    assert body["golden_answer"]["answers"][0]["student_answer"] == imported_case.golden_answer.answers[0].student_answer
    assert len(body["predictions"]) == len(imported_case.predictions)


def test_case_detail_falls_back_to_fixture_case() -> None:
    client = TestClient(app)

    response = client.get("/cases/handwrite233")

    assert response.status_code == 200
    assert response.json()["case_id"] == "handwrite233"


def test_case_detail_returns_404_for_missing_case() -> None:
    client = TestClient(app)

    response = client.get("/cases/missing-case-detail")

    assert response.status_code == 404
    assert "missing-case-detail" in response.json()["detail"]

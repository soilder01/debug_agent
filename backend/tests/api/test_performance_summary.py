from fastapi.testclient import TestClient

from debug_agent.main import app
from debug_agent.telemetry.performance import performance_recorder, record_performance_event


def test_performance_summary_returns_aggregates_and_recent_events() -> None:
    client = TestClient(app)
    performance_recorder.clear()
    try:
        record_performance_event(component="lark_cli", operation="+csv-get", duration_ms=10)
        record_performance_event(component="lark_cli", operation="+csv-get", duration_ms=30)
        record_performance_event(component="lark_cli", operation="+cells-set", duration_ms=50, status="failed")

        response = client.get("/performance/summary?component=lark_cli&limit=2")

        assert response.status_code == 200
        body = response.json()
        assert body["total_count"] == 3
        csv_get = next(item for item in body["aggregates"] if item["operation"] == "+csv-get")
        assert csv_get["component"] == "lark_cli"
        assert csv_get["count"] == 2
        assert csv_get["failed_count"] == 0
        assert csv_get["avg_ms"] == 20
        assert body["recent_events"][-1]["operation"] == "+cells-set"
        assert body["recent_events"][-1]["status"] == "failed"
    finally:
        performance_recorder.clear()


def test_api_middleware_records_request_duration() -> None:
    client = TestClient(app)
    performance_recorder.clear()
    try:
        health_response = client.get("/health")
        assert health_response.status_code == 200

        response = client.get("/performance/summary?component=api")

        assert response.status_code == 200
        operations = {item["operation"] for item in response.json()["recent_events"]}
        assert "GET /health" in operations
    finally:
        performance_recorder.clear()

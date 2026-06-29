import asyncio

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.models.credentials import get_model_credential
from debug_agent.main import app


def test_batch_submission_creates_progress_resource_and_controls() -> None:
    client = TestClient(app)

    response = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233", "missing-case"], "baseline_trials": 1, "max_concurrency": 3},
    )

    assert response.status_code == 202
    body = response.json()
    batch_id = body["batch_id"]
    assert body["batch"]["batch"]["batch_id"] == batch_id
    assert body["batch"]["batch"]["max_concurrency"] == 3
    assert body["batch"]["pending_count"] == 1
    assert body["batch"]["evaluation_summary"]["row_count"] == 2
    assert body["batch"]["evaluation_summary"]["created_jobs"] == 1
    assert body["batch"]["evaluation_summary"]["pending_jobs"] == 1
    assert body["batch"]["evaluation_summary"]["speed_label"] == "等待基线"
    assert body["rejected_case_ids"] == ["missing-case"]
    assert body["jobs"][0]["artifact_group_id"] == batch_id

    detail = client.get(f"/debug-batches/{batch_id}")
    assert detail.status_code == 200
    assert detail.json()["status_counts"]["created"] == 1

    pause = client.post(f"/debug-batches/{batch_id}/pause")
    assert pause.status_code == 200
    assert pause.json()["batch"]["status"] == "paused"

    resume = client.post(f"/debug-batches/{batch_id}/resume")
    assert resume.status_code == 200
    assert resume.json()["batch"]["status"] == "running"

    cancel = client.post(f"/debug-batches/{batch_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["batch"]["status"] == "cancelled"

    routes.job_repository.mark_failed(body["jobs"][0]["job_id"], "test cleanup")


def test_batch_progress_includes_round4_evaluation_after_completion() -> None:
    client = TestClient(app)

    response = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233"], "baseline_trials": 1, "max_concurrency": 1},
    )

    assert response.status_code == 202
    body = response.json()
    batch_id = body["batch_id"]
    job_id = body["jobs"][0]["job_id"]

    asyncio.run(routes.job_service.run_job(job_id))

    detail = client.get(f"/debug-batches/{batch_id}")
    assert detail.status_code == 200
    evaluation = detail.json()["evaluation_summary"]
    assert evaluation["completed_jobs"] == 1
    assert evaluation["success_rate"] == 1
    assert evaluation["model_call_count"] == 6
    assert evaluation["model_call_errors"] == 0
    assert evaluation["cost_label"] == "无模型成本"
    assert evaluation["trust_label"] == "可信"
    assert "速度=" in evaluation["comparison_summary"]


def test_batch_comparison_api_ranks_batches_without_unlocking_model_runner() -> None:
    client = TestClient(app)

    first = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233"], "baseline_trials": 1, "max_concurrency": 1},
    )
    second = client.post(
        "/debug-jobs/batch",
        json={
            "case_ids": ["handwrite233"],
            "baseline_trials": 1,
            "max_concurrency": 1,
            "agent_model_config": {
                "roles": {
                    "model_runner": {
                        "provider": "ark",
                        "model_id": "unsafe-custom-model",
                        "thinking": "enabled",
                    },
                    "report_root_cause": {
                        "provider": "ark",
                        "model_id": "report-thinking-model",
                        "thinking": "enabled",
                    },
                }
            },
        },
    )
    first_body = first.json()
    second_body = second.json()
    asyncio.run(routes.job_service.run_job(first_body["jobs"][0]["job_id"]))

    response = client.get(
        f"/api/debug-batches/comparison?batch_ids={first_body['batch_id']},{second_body['batch_id']}"
    )
    csv_response = client.get(
        f"/api/debug-batches/comparison.csv?batch_ids={first_body['batch_id']},{second_body['batch_id']}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["batch_ids"] == [first_body["batch_id"], second_body["batch_id"]]
    assert body["best_batch_id"] == first_body["batch_id"]
    assert "model_runner 公平复测锁定" in body["summary"]
    assert body["items"][0]["model_runner_locked"] is True
    assert body["items"][0]["quality_score"] > body["items"][1]["quality_score"]
    assert csv_response.status_code == 200
    assert "debug-batch-comparison.csv" in csv_response.headers["content-disposition"]
    assert "model_runner_locked" in csv_response.text


def test_pilot_gate_uses_readiness_and_batch_comparison_for_go_no_go() -> None:
    client = TestClient(app)

    first = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233"], "baseline_trials": 1, "max_concurrency": 1},
    )
    second = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233"], "baseline_trials": 1, "max_concurrency": 1},
    )
    first_body = first.json()
    asyncio.run(routes.job_service.run_job(first_body["jobs"][0]["job_id"]))

    response = client.get(
        "/api/operations/pilot-gate"
        "?limit=2&min_completed_jobs=1&min_success_rate=0.5&max_p95_duration_ms=999999"
        "&max_estimated_cost_units=100&max_model_call_errors=0&max_writeback_failed=0"
        "&max_lark_operation_failures=0"
    )

    assert response.status_code == 200
    body = response.json()
    assert first_body["batch_id"] in body["comparison"]["batch_ids"]
    assert body["batch_evidence"]["completed_jobs"] >= 1
    assert body["comparison"]["best_batch_id"] == first_body["batch_id"]
    assert body["thresholds"]["min_completed_jobs"] == 1
    assert body["export_urls"]["batch_comparison_csv"].startswith("/api/debug-batches/comparison.csv")
    check_keys = {check["key"] for check in body["checks"]}
    assert {"production_readiness", "scale_coverage", "model_runner_fairness"} <= check_keys
    assert any(check["status"] in {"passed", "warning"} for check in body["checks"] if check["key"] == "model_runner_fairness")
    routes.job_repository.mark_failed(second.json()["jobs"][0]["job_id"], "test cleanup")


def test_batch_submission_persists_agent_model_config_with_locked_model_runner() -> None:
    client = TestClient(app)

    response = client.post(
        "/debug-jobs/batch",
        json={
            "case_ids": ["handwrite233"],
            "baseline_trials": 1,
            "agent_model_config": {
                "roles": {
                    "model_runner": {
                        "provider": "ark",
                        "model_id": "unsafe-custom-model",
                        "thinking": "enabled",
                    },
                    "report_root_cause": {
                        "provider": "ark",
                        "model_id": "report-model",
                        "thinking": "enabled",
                        "temperature": 0.1,
                    },
                }
            },
        },
    )

    assert response.status_code == 202
    body = response.json()
    retry_policy = body["batch"]["batch"]["retry_policy"]
    roles = retry_policy["agent_model_config"]["roles"]
    assert roles["model_runner"]["model_id"] != "unsafe-custom-model"
    assert roles["model_runner"]["locked"] is True
    assert roles["report_root_cause"]["model_id"] == "report-model"

    routes.job_repository.mark_failed(body["jobs"][0]["job_id"], "test cleanup")


def test_agent_model_catalog_exposes_default_locked_source_model() -> None:
    client = TestClient(app)

    response = client.get("/agent-models")

    assert response.status_code == 200
    body = response.json()
    roles = body["runtime"]["default_config"]["roles"]
    assert roles["model_runner"]["locked"] is True
    assert roles["model_runner"]["thinking"] == "disabled"
    assert body["runtime"]["catalog"][0]["locked_for_roles"] == ["model_runner"]


def test_agent_model_connection_test_does_not_persist_api_key(monkeypatch) -> None:
    client = TestClient(app)

    def fake_fetch(*, base_url: str, api_key: str) -> list[str]:
        assert base_url == "https://example.test/v1"
        assert api_key == "secret-key"
        return ["custom-model"]

    monkeypatch.setattr(routes, "_fetch_compatible_model_ids", fake_fetch)

    response = client.post(
        "/agent-models/test",
        json={
            "provider": "api",
            "base_url": "https://example.test/v1",
            "api_key": "secret-key",
            "model_id": "custom-model",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["message"] == "连接成功；API key 已保存为当前后端会话凭据引用，不会明文写入任务配置或持久库。"
    assert body["model_count"] == 1
    assert body["model_found"] is True
    assert body["credential_ref"].startswith("model-cred-")
    assert body["credential_ref"] != "secret-key"
    assert get_model_credential(body["credential_ref"]) == "secret-key"

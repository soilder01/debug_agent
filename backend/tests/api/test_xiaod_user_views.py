from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app


def test_xiaod_job_view_wraps_internal_job_json_as_user_page() -> None:
    client = TestClient(app)
    submitted = client.post("/cases/handwrite233/debug").json()
    job_id = submitted["job_id"]

    response = client.get(f"/xiaod/views/jobs/{job_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Debug 任务详情" in response.text
    assert "小D 用户视图" in response.text
    assert "查看运行阶段" in response.text
    assert "查看证据链" in response.text
    assert "结构化 API" in response.text
    assert f"/jobs/{job_id}" in response.text


def test_xiaod_report_view_has_friendly_pending_state_before_report_exists() -> None:
    client = TestClient(app)
    job_id = "xiaod-view-pending-report"
    routes.job_repository.create_job(job_id=job_id, case_id="missing-case-for-report-view")

    response = client.get(f"/xiaod/views/jobs/{job_id}/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "报告还没有生成" in response.text
    assert "查看任务进度" in response.text
    assert "报告 JSON" in response.text


def test_xiaod_batch_view_wraps_batch_progress() -> None:
    client = TestClient(app)
    batch = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233"], "baseline_trials": 1, "max_concurrency": 1},
    ).json()

    response = client.get(f"/xiaod/views/debug-batches/{batch['batch_id']}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Debug 批次概览" in response.text
    assert "运行质量" in response.text
    assert "最近任务" in response.text
    assert "/xiaod/views/jobs/" in response.text


def test_xiaod_manual_view_lists_enterprise_knowledge_documents() -> None:
    client = TestClient(app)

    response = client.get("/xiaod/views/manual")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Debug Agent 企业级落地手册" in response.text
    assert "提交 badcase" in response.text
    assert "表格重跑" in response.text
    assert "报告阅读" in response.text
    assert "RAG知识库" in response.text
    assert "enterprise_delivery_handbook.md" in response.text
    assert ">500" not in response.text

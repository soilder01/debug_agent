from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app


def test_job_report_api_returns_report_from_persisted_job_evidence() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["case_id"] == "handwrite233"
    assert body["experiment_summary"]["total_trials"] == 10
    assert len(body["experiment_summary"]["evidence_ids"]) == 10
    assert body["root_cause"]["label"] == "answer_mismatch"
    assert body["root_cause"]["confidence"] == "high"
    assert body["product_summary"]["root_cause_label"] == "答案与标答不一致 / 高置信"
    assert body["product_summary"]["evidence_source"]
    assert body["product_summary"]["confidence_explanation"]
    assert body["product_summary"]["next_action"]
    assert body["observed_failure"]["type"] == "answer_mismatch"
    assert body["observed_failure"]["affected_box_ids"]
    assert body["agent_traces"]
    first_trace = body["agent_traces"][0]
    assert first_trace["agent_role"] == "model_runner"
    assert first_trace["input_excerpt"]
    assert first_trace["output_excerpt"]
    assert first_trace["raw_cot_policy"] == "visible_output_summary_only"


def test_job_report_api_returns_404_for_missing_job() -> None:
    client = TestClient(app)

    response = client.get("/jobs/missing-job/report")

    assert response.status_code == 404


def test_job_report_api_includes_published_lark_report_document_url() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    routes.job_repository.save_lark_report_document(
        job_id=job_id,
        status="published",
        document_url="https://bytedance.larkoffice.com/docx/doc-token",
        document_token="doc-token",
        internal_report_url=f"http://localhost:8000/jobs/{job_id}/report",
    )

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    assert (
        response.json()["report_document_url"] == "https://bytedance.larkoffice.com/docx/doc-token"
    )


def test_job_report_api_includes_supplemental_context() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="supplemental_context",
        status="completed",
        input={
            "supplement_text": "补充材料：视频第 2 秒右侧按钮闪了一下。",
            "attachments": [{"type": "file", "file_key": "file_v2_extra", "name": "extra.mp4"}],
            "actor": "ou_debugger",
        },
        output={
            "draft_id": "draft-1",
            "job_id": job_id,
            "message_id": "om_supplement_1",
            "attachment_count": 1,
        },
        failure_reason="",
        retryable=False,
    )

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    supplemental_context = response.json()["supplemental_contexts"][0]
    assert supplemental_context["text"] == "补充材料：视频第 2 秒右侧按钮闪了一下。"
    assert supplemental_context["message_id"] == "om_supplement_1"
    assert supplemental_context["attachment_count"] == 1
    assert supplemental_context["attachments"][0]["file_key"] == "file_v2_extra"

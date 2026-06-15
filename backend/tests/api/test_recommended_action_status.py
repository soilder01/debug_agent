from uuid import uuid4

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_recommended_action_status_api_updates_and_lists_status() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": "prompt fix approved"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["action_index"] == 0
    assert body["status"] == "accepted"
    assert body["actor"] == "qa-reviewer"
    assert body["note"] == "prompt fix approved"
    assert body["updated_at"]
    assert routes.job_repository.list_recommended_action_statuses(job_id)[0].status == "accepted"

    list_response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")
    assert list_response.status_code == 200
    assert list_response.json()["statuses"] == [body]


def test_recommended_action_status_api_lists_status_events() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()
    first_response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": "prompt fix approved"},
    )
    second_response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "applied", "actor": "owner", "note": "prompt fix landed"},
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")

    assert response.status_code == 200
    body = response.json()
    assert [event["status"] for event in body["events"]] == ["accepted", "applied"]
    assert [event["actor"] for event in body["events"]] == ["qa-reviewer", "owner"]
    assert body["events"][0]["action_index"] == 0
    assert body["events"][0]["note"] == "prompt fix approved"
    assert body["events"][0]["created_at"]


def test_recommended_action_status_api_uses_local_dev_actor_fallback() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "accepted", "note": "approved without actor"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["actor"] == "local-dev-operator"
    list_response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")
    assert list_response.status_code == 200
    assert list_response.json()["events"][0]["actor"] == "local-dev-operator"


def test_recommended_action_status_api_rejects_empty_actor_when_trusted_actor_required(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "settings",
        routes.settings.model_copy(update={"require_trusted_actor": True}),
    )
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "accepted", "actor": "   ", "note": "missing trusted actor"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Actor is required when trusted actor enforcement is enabled."


def test_recommended_action_status_api_creates_verification_job_link() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/recommended-actions/0/verification-jobs",
        json={"actor": "frontend-operator", "note": "verify applied prompt fix"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == job_id
    assert body["action_index"] == 0
    assert body["actor"] == "frontend-operator"
    assert body["note"] == "verify applied prompt fix"
    assert body["verification_job"]["case_id"].startswith("case-action-status-")
    assert body["verification_job_id"] == body["verification_job"]["job_id"]
    assert body["verification_job"]["status"] == "created"

    list_response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")
    assert list_response.status_code == 200
    assert list_response.json()["verifications"] == [
        {
            "job_id": job_id,
            "action_index": 0,
            "verification_job_id": body["verification_job_id"],
            "actor": "frontend-operator",
            "note": "verify applied prompt fix",
            "created_at": body["created_at"],
        }
    ]
    routes.job_repository.mark_failed(body["verification_job_id"], "test cleanup")


def test_recommended_action_verification_api_uses_local_dev_actor_fallback() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/recommended-actions/0/verification-jobs",
        json={"note": "verify without actor"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["actor"] == "local-dev-operator"
    assert body["note"] == "verify without actor"
    routes.job_repository.mark_failed(body["verification_job_id"], "test cleanup")


def test_recommended_action_verification_api_rejects_empty_actor_when_trusted_actor_required(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "settings",
        routes.settings.model_copy(update={"require_trusted_actor": True}),
    )
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/recommended-actions/0/verification-jobs",
        json={"actor": "", "note": "missing trusted actor"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Actor is required when trusted actor enforcement is enabled."


def test_recommended_action_status_api_evaluates_resolved_verification_job() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()
    verification_response = client.post(
        f"/jobs/{job_id}/recommended-actions/0/verification-jobs",
        json={"actor": "frontend-operator", "note": "verify applied prompt fix"},
    )
    assert verification_response.status_code == 202
    verification_job_id = verification_response.json()["verification_job_id"]
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.save_evidence(
        job_id=verification_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{verification_job_id}:baseline-pass",
                step_name="baseline_replay",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id=f"{verification_job_id}:ablation-pass",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    routes.job_repository.mark_completed(verification_job_id)

    response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")

    assert response.status_code == 200
    body = response.json()
    assert body["verification_results"] == [
        {
            "job_id": job_id,
            "action_index": 0,
            "verification_job_id": verification_job_id,
            "result": "resolved",
            "source_success_rate": 0.5,
            "verification_success_rate": 1.0,
            "source_root_cause": "single_modality_capability_gap",
            "verification_root_cause": "output_mismatch",
            "summary": "验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。",
        }
    ]


def test_recommended_action_status_api_marks_incomplete_verification_pending() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()
    verification_response = client.post(
        f"/jobs/{job_id}/recommended-actions/0/verification-jobs",
        json={"actor": "frontend-operator", "note": "verify applied prompt fix"},
    )
    assert verification_response.status_code == 202
    verification_job_id = verification_response.json()["verification_job_id"]
    routes.job_repository.mark_failed(verification_job_id, "test keeps verification pending without queue pollution")

    response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")

    assert response.status_code == 200
    body = response.json()
    assert body["verification_results"] == [
        {
            "job_id": job_id,
            "action_index": 0,
            "verification_job_id": verification_job_id,
            "result": "pending",
            "source_success_rate": 0.5,
            "verification_success_rate": 0.0,
            "source_root_cause": "single_modality_capability_gap",
            "verification_root_cause": "",
            "summary": "验证任务尚未完成，等待复测结果后再判断推荐操作是否生效。",
        }
    ]


def test_recommended_action_status_api_returns_404_for_missing_job() -> None:
    client = TestClient(app)

    response = client.patch(
        "/jobs/missing-job/recommended-actions/0/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Debug job not found: missing-job"


def test_recommended_action_status_api_returns_404_for_missing_action_index() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.patch(
        f"/jobs/{job_id}/recommended-actions/99/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommended action not found: 99"


def test_recommended_action_verification_returns_404_for_missing_action_index() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/recommended-actions/99/verification-jobs",
        json={"actor": "frontend-operator", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommended action not found: 99"


def _create_job_with_recommended_actions() -> str:
    job_id = f"job-action-status-{uuid4()}"
    case = DebugCase.model_validate(
        {
            "case_id": f"case-action-status-{uuid4()}",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal.mp4",
            "prompt": "Compare image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches image",
                        "actual": "caption says cat but image shows dog",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    routes.job_repository.save_case(case)
    routes.job_repository.create_job(job_id=job_id, case_id=case.case_id)
    routes.job_repository.save_evidence(
        job_id=job_id,
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{job_id}:image-only",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id=f"{job_id}:text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    return job_id

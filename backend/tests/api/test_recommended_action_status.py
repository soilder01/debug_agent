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

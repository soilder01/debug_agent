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


def test_strategy_follow_up_api_creates_traceable_debug_job() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/strategy-follow-ups/evidence_audit/debug-jobs",
        json={"actor": "strategy-operator", "note": "run evidence audit probe"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_job_id"] == job_id
    assert body["stage"] == "evidence_audit"
    assert body["planned_steps"] == "strategy_evidence_audit_probe"
    assert body["actor"] == "strategy-operator"
    assert body["note"] == "run evidence audit probe"
    assert body["follow_up_job_id"] == body["follow_up_job"]["job_id"]
    assert body["follow_up_job"]["status"] == "created"

    list_response = client.get(f"/jobs/{job_id}/strategy-follow-ups")
    assert list_response.status_code == 200
    assert list_response.json()["follow_ups"] == [
        {
            "source_job_id": job_id,
            "stage": "evidence_audit",
            "planned_steps": "strategy_evidence_audit_probe",
            "follow_up_job_id": body["follow_up_job_id"],
            "actor": "strategy-operator",
            "note": "run evidence audit probe",
            "created_at": body["created_at"],
            "outcome": "pending",
            "success_rate": 0.0,
            "summary": "Strategy follow-up job is not completed yet.",
            "escalation": "",
        }
    ]
    routes.job_repository.mark_failed(body["follow_up_job_id"], "test cleanup")


def test_strategy_follow_up_api_evaluates_completed_follow_up_outcome() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()
    create_response = client.post(
        f"/jobs/{job_id}/strategy-follow-ups/evidence_audit/debug-jobs",
        json={"actor": "strategy-operator", "note": "run evidence audit probe"},
    )
    assert create_response.status_code == 202
    follow_up_job_id = create_response.json()["follow_up_job_id"]
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.save_evidence(
        job_id=follow_up_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{follow_up_job_id}:strategy-pass",
                step_name="strategy_evidence_audit_probe",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    routes.job_repository.mark_completed(follow_up_job_id)

    response = client.get(f"/jobs/{job_id}/strategy-follow-ups")

    assert response.status_code == 200
    follow_up = response.json()["follow_ups"][0]
    assert follow_up["outcome"] == "passed_stop_condition"
    assert follow_up["success_rate"] == 1.0
    assert follow_up["summary"] == "Strategy follow-up job passed all probes; stop condition is likely satisfied."
    assert follow_up["escalation"] == ""


def test_strategy_follow_up_api_creates_escalation_debug_job_from_failed_strategy_outcome() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    create_response = client.post(
        f"/jobs/{job_id}/strategy-follow-ups/ablation_expansion/debug-jobs",
        json={"actor": "strategy-operator", "note": "run ablation expansion"},
    )
    assert create_response.status_code == 202
    failed_follow_up_job_id = create_response.json()["follow_up_job_id"]
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.save_evidence(
        job_id=failed_follow_up_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{failed_follow_up_job_id}:strategy-fail",
                step_name="strategy_ablation_expansion_probe",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    routes.job_repository.mark_completed(failed_follow_up_job_id)

    response = client.post(
        f"/jobs/{job_id}/strategy-follow-ups/ablation_expansion/debug-jobs",
        json={"actor": "strategy-operator", "note": "run escalation probe"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["stage"] == "ablation_expansion"
    assert body["planned_steps"] == "strategy_escalation_single_modality_probe"
    assert body["note"] == "run escalation probe"
    routes.job_repository.mark_failed(failed_follow_up_job_id, "test cleanup after completed follow-up")
    routes.job_repository.mark_failed(body["follow_up_job_id"], "test cleanup")


def test_strategy_follow_up_api_rejects_unknown_stage() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.post(
        f"/jobs/{job_id}/strategy-follow-ups/missing_stage/debug-jobs",
        json={"actor": "strategy-operator", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Strategy follow-up stage not found: missing_stage"


def test_targeted_probe_api_creates_traceable_debug_job() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()

    response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "probe conflict target"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_job_id"] == job_id
    assert body["source"] == "targeted_probe"
    assert body["target_id"] == "multimodal:conflict:1"
    assert body["planned_steps"] == "targeted_multimodal_conflict_probe"
    assert body["parent_probe_job_id"] == ""
    assert body["trigger_outcome"] == ""
    assert body["actor"] == "targeted-operator"
    assert body["note"] == "probe conflict target"
    assert body["probe_job_id"] == body["probe_job"]["job_id"]
    assert body["probe_job"]["status"] == "created"
    routes.job_repository.mark_failed(body["probe_job_id"], "test cleanup")


def test_targeted_probe_api_rejects_unknown_target() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()

    response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:missing/debug-jobs",
        json={"actor": "targeted-operator", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Targeted probe not found: multimodal:conflict:missing"


def test_targeted_probe_api_lists_pending_probe_history() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    create_response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "probe conflict target"},
    )
    assert create_response.status_code == 202
    probe_job_id = create_response.json()["probe_job_id"]

    response = client.get(f"/jobs/{job_id}/targeted-probes")

    assert response.status_code == 200
    assert response.json()["probes"] == [
        {
            "source_job_id": job_id,
            "source": "targeted_probe",
            "target_id": "multimodal:conflict:1",
            "planned_steps": "targeted_multimodal_conflict_probe",
            "probe_job_id": probe_job_id,
            "parent_probe_job_id": "",
            "trigger_outcome": "",
            "actor": "targeted-operator",
            "note": "probe conflict target",
            "created_at": create_response.json()["created_at"],
            "outcome": "pending",
            "success_rate": 0.0,
            "summary": "Targeted probe job is not completed yet.",
            "escalation": "",
        }
    ]
    routes.job_repository.mark_failed(probe_job_id, "test cleanup")


def test_targeted_probe_api_evaluates_completed_probe_outcome() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    create_response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "probe conflict target"},
    )
    assert create_response.status_code == 202
    probe_job_id = create_response.json()["probe_job_id"]
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.save_evidence(
        job_id=probe_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{probe_job_id}:targeted-fail",
                step_name="targeted_multimodal_conflict_probe",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    routes.job_repository.mark_completed(probe_job_id)

    response = client.get(f"/jobs/{job_id}/targeted-probes")

    assert response.status_code == 200
    probe = response.json()["probes"][0]
    assert probe["outcome"] == "target_still_failing"
    assert probe["success_rate"] == 0.0
    assert probe["summary"] == "Targeted probe still failed on multimodal:conflict:1; escalation is recommended."
    assert probe["escalation"] == "Run deeper localized replay or modality-specific probes for multimodal:conflict:1."
    routes.job_repository.mark_failed(probe_job_id, "test cleanup after completed probe")


def test_targeted_probe_api_creates_escalation_job_with_parent_probe_lineage() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    first_response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "probe conflict target"},
    )
    assert first_response.status_code == 202
    first_probe_job_id = first_response.json()["probe_job_id"]
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.save_evidence(
        job_id=first_probe_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{first_probe_job_id}:targeted-fail",
                step_name="targeted_multimodal_conflict_probe",
                trial=0,
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            )
        ],
    )
    routes.job_repository.mark_completed(first_probe_job_id)

    response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "escalate conflict target"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source"] == "targeted_probe_outcome"
    assert body["planned_steps"] == "targeted_escalation_multimodal_conflict_probe"
    assert body["parent_probe_job_id"] == first_probe_job_id
    assert body["trigger_outcome"] == "target_still_failing"
    assert body["note"] == "escalate conflict target"
    routes.job_repository.mark_failed(body["probe_job_id"], "test cleanup")
    routes.job_repository.mark_failed(first_probe_job_id, "test cleanup after completed probe")


def test_targeted_probe_api_stops_escalation_when_guardrail_blocks_target() -> None:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    parent_probe_job_id = ""
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    for index in range(3):
        response = client.post(
            f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
            json={"actor": "targeted-operator", "note": f"probe round {index + 1}"},
        )
        assert response.status_code == 202
        probe_job_id = response.json()["probe_job_id"]
        if index > 0:
            assert response.json()["parent_probe_job_id"] == parent_probe_job_id
        routes.job_repository.save_evidence(
            job_id=probe_job_id,
            case_id=source_job.case_id,
            evidence=[
                ExperimentEvidence(
                    evidence_id=f"{probe_job_id}:targeted-fail",
                    step_name="targeted_multimodal_conflict_probe",
                    trial=0,
                    raw_output="{\"conflicts\":[]}",
                    judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
                )
            ],
        )
        routes.job_repository.mark_completed(probe_job_id)
        parent_probe_job_id = probe_job_id

    response = client.post(
        f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
        json={"actor": "targeted-operator", "note": "probe past guardrail"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Targeted probe stopped by guardrail for multimodal:conflict:1: max_targeted_probe_depth_reached"
    )
    routes.job_repository.mark_failed(parent_probe_job_id, "test cleanup after completed probe")


def test_human_handoff_status_api_updates_and_lists_guardrail_handoff() -> None:
    client = TestClient(app)
    job_id = _create_job_with_targeted_probe_guardrail()

    response = client.patch(
        f"/jobs/{job_id}/human-handoffs/multimodal:conflict:1/status",
        json={"status": "in_progress", "actor": "human-debugger", "note": "reviewing full probe chain"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["target_id"] == "multimodal:conflict:1"
    assert body["status"] == "in_progress"
    assert body["actor"] == "human-debugger"
    assert body["note"] == "reviewing full probe chain"
    assert body["updated_at"]

    list_response = client.get(f"/jobs/{job_id}/human-handoffs/statuses")
    assert list_response.status_code == 200
    assert list_response.json()["statuses"] == [body]


def test_human_handoff_status_api_rejects_unknown_handoff_target() -> None:
    client = TestClient(app)
    job_id = _create_job_with_targeted_probe_guardrail()

    response = client.patch(
        f"/jobs/{job_id}/human-handoffs/multimodal:conflict:missing/status",
        json={"status": "in_progress", "actor": "human-debugger", "note": "unknown target"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Human handoff target not found: multimodal:conflict:missing"


def test_final_attribution_follow_up_api_creates_traceable_verification_job() -> None:
    client = TestClient(app)
    job_id = _create_job_with_targeted_probe_guardrail()
    routes.job_repository.save_human_handoff_status(
        job_id=job_id,
        target_id="multimodal:conflict:1",
        status="resolved",
        actor="human-debugger",
        note="Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
    )

    response = client.post(
        f"/jobs/{job_id}/final-attributions/multimodal:conflict:1/verification-jobs",
        json={"actor": "final-attribution-operator", "note": "verify prompt attribution fix"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_job_id"] == job_id
    assert body["stage"] == "final_attribution:multimodal:conflict:1"
    assert body["planned_steps"] == "final_attribution_prompt_verification"
    assert body["actor"] == "final-attribution-operator"
    assert body["note"] == "verify prompt attribution fix"
    assert body["follow_up_job_id"] == body["follow_up_job"]["job_id"]
    assert body["follow_up_job"]["status"] == "created"

    list_response = client.get(f"/jobs/{job_id}/strategy-follow-ups")
    assert list_response.status_code == 200
    assert any(
        follow_up["stage"] == "final_attribution:multimodal:conflict:1"
        and follow_up["planned_steps"] == "final_attribution_prompt_verification"
        for follow_up in list_response.json()["follow_ups"]
    )
    routes.job_repository.mark_failed(body["follow_up_job_id"], "test cleanup")


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


def _create_job_with_cross_modal_strategy() -> str:
    job_id = f"job-cross-modal-strategy-{uuid4()}"
    case = DebugCase.model_validate(
        {
            "case_id": f"case-cross-modal-strategy-{uuid4()}",
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
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id=f"{job_id}:text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id=f"{job_id}:cross-modal",
                step_name="modality_ablation_check",
                trial=2,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
            ),
        ],
    )
    return job_id


def _create_job_with_targeted_probe_guardrail() -> str:
    client = TestClient(app)
    job_id = _create_job_with_cross_modal_strategy()
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    parent_probe_job_id = ""
    for index in range(3):
        response = client.post(
            f"/jobs/{job_id}/targeted-probes/multimodal:conflict:1/debug-jobs",
            json={"actor": "targeted-operator", "note": f"probe round {index + 1}"},
        )
        assert response.status_code == 202
        probe_job_id = response.json()["probe_job_id"]
        routes.job_repository.save_evidence(
            job_id=probe_job_id,
            case_id=source_job.case_id,
            evidence=[
                ExperimentEvidence(
                    evidence_id=f"{probe_job_id}:targeted-fail",
                    step_name="targeted_multimodal_conflict_probe",
                    trial=0,
                    raw_output="{\"conflicts\":[]}",
                    judge=JudgeResult(score=0, reasons=["multimodal:conflict:1 conflict_actual_mismatch"]),
                )
            ],
        )
        routes.job_repository.mark_completed(probe_job_id)
        parent_probe_job_id = probe_job_id
    assert parent_probe_job_id
    return job_id

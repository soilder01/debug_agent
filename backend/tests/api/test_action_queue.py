from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_action_queue_api_returns_traceable_stateful_items() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()
    verification_job_id = _create_verification_job(source_job_id=job_id, score=1)
    routes.job_repository.save_recommended_action_status(
        job_id=job_id,
        action_index=0,
        status="applied",
        actor="case-owner",
        note="prompt fix landed",
    )
    routes.job_repository.save_recommended_action_verification(
        job_id=job_id,
        action_index=0,
        verification_job_id=verification_job_id,
        actor="case-owner",
        note="verify prompt fix",
    )
    routes.job_repository.save_spreadsheet_writeback_audit(
        job_id=job_id,
        status="succeeded",
        row_id="row-42",
        report_url=f"https://debug-agent.local/jobs/{job_id}/report",
        fields={"错误原因": "模型时序输出不稳定"},
        error_message="",
    )

    response = client.get(f"/jobs/{job_id}/action-queue")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["summary"]["total"] >= 1
    item = body["items"][0]
    assert item["id"] == "recommended:0"
    assert item["kind"] == "recommended_action"
    assert item["state"] == "verified"
    assert item["state_label"] == "已通过"
    assert item["status"] == "applied"
    assert item["owner"] == "case-owner"
    assert item["source"] == "prompt"
    assert item["source_ref"] == "report.recommended_actions[0]"
    assert item["verification_job_id"] == verification_job_id
    assert item["verification_result"] == "resolved"
    assert item["writeback_status"] == "succeeded"
    assert item["writeback_row_id"] == "row-42"
    assert "verify" in item["available_operations"]
    assert "writeback" in item["available_operations"]


def test_job_report_embeds_action_queue() -> None:
    client = TestClient(app)
    job_id = _create_job_with_recommended_actions()

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["action_queue"][0]["id"] == "recommended:0"
    assert body["action_queue"][0]["state"] == "pending"
    assert body["action_queue"][0]["owner"] == "debug_agent_operator"


def test_lark_completion_card_shows_action_queue_and_callback_buttons(monkeypatch) -> None:
    unique = uuid4().hex
    job_id = f"job-action-queue-card-{unique}"
    draft = routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这个 badcase",
        input_source="https://example.com/video.mp4",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="同一视频片段多次输出不一致",
        submitted_case_id=f"case-action-queue-card-{unique}",
        submitted_job_id=job_id,
    )
    routes.job_repository.create_job(job_id=job_id, case_id=draft.submitted_case_id)
    job = routes.job_repository.get_job(job_id)
    assert job is not None
    report = SimpleNamespace(
        root_cause=SimpleNamespace(
            label="model_instability",
            confidence="high",
            evidence_summary="baseline 多次复测不稳定。",
        ),
        recommended_actions=[
            {
                "category": "stability",
                "priority": "P0",
                "summary": "补充视频时间窗约束后重跑验证。",
                "status": "pending",
            }
        ],
        action_queue=[
            {
                "id": "recommended:0",
                "kind": "recommended_action",
                "title": "补充视频时间窗约束后重跑验证。",
                "priority": "P0",
                "state": "pending",
                "state_label": "待处理",
                "owner": "debug_agent_operator",
                "verification_job_id": "",
                "writeback_status": "not_requested",
            }
        ],
        follow_up_experiments=[],
        meta_agent_enrichment={},
        agent_traces=[],
    )
    monkeypatch.setattr(
        routes,
        "build_report_for_job",
        lambda repository, requested_job_id: report if requested_job_id == job_id else None,
    )

    card = routes._lark_bot_completion_card(
        draft=draft,
        job=job,
        job_url=f"https://debug-agent.local/jobs/{job_id}",
        report_url=f"https://debug-agent.local/jobs/{job_id}/report",
        internal_report_url=f"https://debug-agent.local/jobs/{job_id}/report",
        report_document=None,
        markdown="",
    )

    content = card["elements"][0]["content"]
    assert "**Action Queue**：1 项，待处理 1 项" in content
    labels = [action["text"]["content"] for action in card["elements"][1]["actions"]]
    assert "接受首个动作" in labels
    assert "验证首个动作" in labels
    assert "转人工处理" in labels
    callback_values = [
        action["behaviors"][0]["value"]
        for action in card["elements"][1]["actions"]
        if action.get("behaviors")
    ]
    assert {
        "action": "action_queue_accept",
        "job_id": job_id,
        "action_index": 0,
    } in callback_values
    assert {
        "action": "action_queue_verify",
        "job_id": job_id,
        "action_index": 0,
    } in callback_values


def test_lark_card_action_accepts_action_queue_item() -> None:
    job_id = _create_job_with_recommended_actions()

    result = routes._handle_lark_bot_card_action_event(
        {
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "action": {
                    "value": {
                        "action": "action_queue_accept",
                        "job_id": job_id,
                        "action_index": 0,
                    }
                },
                "operator": {"open_id": "ou-action-owner"},
            },
        }
    )

    assert result is not None
    assert result["handled"] is True
    assert result["action"] == "action_queue_accept"
    assert result["toast"] == {"type": "success", "content": "已接受 Action Queue 动作。"}
    status = routes.job_repository.list_recommended_action_statuses(job_id)[0]
    assert status.status == "accepted"
    assert status.actor == "ou-action-owner"


def _create_job_with_recommended_actions() -> str:
    job_id = f"job-action-queue-{uuid4()}"
    case = DebugCase.model_validate(
        {
            "case_id": f"case-action-queue-{uuid4()}",
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
            "predictions": [{"trial": 0, "raw_output": '{"conflicts":[]}', "score": 0}],
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
                request_summary={
                    "ablation_variant": "image_only",
                    "ablation_modalities": ["image"],
                },
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["multimodal:conflict:1 conflict_actual_mismatch"],
                ),
            ),
            ExperimentEvidence(
                evidence_id=f"{job_id}:text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={
                    "ablation_variant": "text_only",
                    "ablation_modalities": ["text"],
                },
                raw_output='{"conflicts":[]}',
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    return job_id


def _create_verification_job(*, source_job_id: str, score: int) -> str:
    source_job = routes.job_repository.get_job(source_job_id)
    assert source_job is not None
    verification_job_id = f"{source_job_id}__action_verify__{uuid4().hex}"
    routes.job_repository.create_job(job_id=verification_job_id, case_id=source_job.case_id)
    routes.job_repository.save_evidence(
        job_id=verification_job_id,
        case_id=source_job.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{verification_job_id}:verify",
                step_name="recommended_action_verification",
                trial=0,
                raw_output='{"conflicts":[]}',
                judge=JudgeResult(score=score, reasons=[] if score else ["still failing"]),
            )
        ],
    )
    routes.job_repository.mark_completed(verification_job_id)
    return verification_job_id

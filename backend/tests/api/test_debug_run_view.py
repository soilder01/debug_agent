from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_debug_run_view_api_unifies_runtime_state() -> None:
    client = TestClient(app)
    job_id = _create_job_with_runtime_state()

    response = client.get(f"/jobs/{job_id}/run-view")

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["job_id"] == job_id
    assert body["job"]["status"] == "completed"
    assert body["job"]["status_label"] == "已完成"
    assert body["summary"]["headline"] == "Debug 任务已完成"
    assert body["summary"]["next_step"] == "已验证通过并写回，可以沉淀修复结论。"
    attribution = next(item for item in body["timeline"] if item["key"] == "attribution")
    assert attribution["status_label"] == "已完成"
    assert any(item["key"] == "auto_closure" for item in body["timeline"])
    assert body["auto_closure"]["status"] == "completed"
    assert body["auto_closure"]["status_label"] == "已完成"
    assert body["writeback"]["status"] == "succeeded"
    assert body["writeback"]["status_label"] == "成功"
    assert body["writeback"]["row_id"] == "row-42"
    assert body["action_queue"]["summary"]["verified"] == 1
    assert body["action_queue"]["items"][0]["state_label"] == "已通过"
    agent_roles = [trace["agent_role"] for trace in body["agent_traces"]]
    assert "report_root_cause" in agent_roles


def test_job_report_embeds_same_debug_run_view() -> None:
    client = TestClient(app)
    job_id = _create_job_with_runtime_state()

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["run_view"]["job"]["job_id"] == job_id
    assert body["run_view"]["action_queue"]["items"][0]["id"] == body["action_queue"][0]["id"]
    assert body["run_view"]["auto_closure"]["status"] == "completed"
    assert body["run_view"]["writeback"]["status"] == "succeeded"


def test_debug_run_view_exposes_hypothesis_closure_matrix() -> None:
    client = TestClient(app)
    job_id = _create_job_with_runtime_state()
    _save_hypothesis_closure_stage(job_id)
    _save_debug_loop_stage(job_id)

    response = client.get(f"/jobs/{job_id}/run-view")

    assert response.status_code == 200
    body = response.json()
    closure = body["hypothesis_closure"]
    debug_loop = body["debug_loop"]
    assert closure["status"] == "completed"
    assert closure["status_label"] == "已完成"
    assert closure["hypothesis_count"] == 1
    assert closure["probe_plan_count"] == 1
    assert closure["causal_comparison_count"] == 1
    assert closure["verified_root_cause_count"] == 0
    assert closure["unverified_hypothesis_count"] == 1
    assert closure["fairness_lock"]["model_runner_config_ref"] == "locked_source"
    assert closure["hypotheses"][0]["status"] == "candidate"
    assert closure["probe_plans"][0]["model_runner_config_ref"] == "locked_source"
    assert closure["causal_comparisons"][0]["verdict"] == "inconclusive"
    assert "1 个候选假设" in closure["summary"]
    assert debug_loop["status"] == "waiting"
    assert debug_loop["current_iteration"] == 1
    assert debug_loop["decision"] == "waiting_for_probe_completion"
    assert debug_loop["iterations"][0]["pending_probe_count"] == 1

    report_response = client.get(f"/jobs/{job_id}/report")
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["run_view"]["hypothesis_closure"] == closure
    assert report_body["run_view"]["debug_loop"] == debug_loop


def test_auto_closure_run_stages_preserve_meta_agent_attribution_traces() -> None:
    job_id = _create_job_with_runtime_state()
    closure = AutoDebugClosureResult(
        source_job_id=job_id,
        final_attribution_candidates=[
            {
                "category": "model_instability",
                "confidence": "high",
                "summary": "闭环复测显示模型时序输出不稳定。",
            }
        ],
        badcase_live_comparison={"decision": "model_instability"},
    )

    routes._save_auto_closure_run_stages(
        repository=routes.job_repository,
        job_id=job_id,
        closure=closure,
    )

    report = routes.build_report_for_job(routes.job_repository, job_id)
    assert report is not None
    agent_roles = {trace.agent_role for trace in report.agent_traces}
    assert "report_root_cause" in agent_roles
    attribution_stage = next(
        stage
        for stage in routes.job_repository.list_debug_run_stages(job_id)
        if stage.stage == "attribution"
    )
    assert "meta_agent_enrichment" in attribution_stage.output
    assert (
        attribution_stage.output["final_attribution_candidates"][0]["category"]
        == "model_instability"
    )


def test_lark_completion_card_uses_debug_run_view_summary(monkeypatch) -> None:
    unique = uuid4().hex
    job_id = f"job-run-view-card-{unique}"
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
        submitted_case_id=f"case-run-view-card-{unique}",
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
        recommended_actions=[],
        action_queue=[],
        follow_up_experiments=[],
        meta_agent_enrichment={},
        agent_traces=[],
        run_view={
            "summary": {
                "headline": "Debug 任务已完成",
                "next_step": "确认报告后执行写回。",
            },
            "auto_closure": {"status_label": "已完成"},
            "debug_loop": {
                "status": "completed",
                "status_label": "已完成",
                "summary": "第 1 轮探索已找到 verified root cause；prompt probe supported.",
                "current_iteration": 1,
                "decision": "verified_root_cause_found",
                "next_action": "查看已验证根因并决定是否同步报告。",
                "stop_reason": "prompt probe supported.",
                "iterations": [
                    {
                        "iteration": 1,
                        "decision": "verified_root_cause_found",
                        "pending_probe_count": 0,
                        "completed_probe_count": 1,
                        "supported_comparison_count": 1,
                    }
                ],
            },
            "hypothesis_closure": {
                "status": "completed",
                "status_label": "已完成",
                "summary": "已生成 1 个候选假设、1 个 probe 计划；prompt probe 已完成。",
                "hypothesis_count": 1,
                "probe_plan_count": 1,
                "probe_result_count": 1,
                "verified_root_cause_count": 1,
                "unverified_hypothesis_count": 0,
                "fairness_lock": {"model_runner_config_ref": "locked_source"},
                "probe_results": [
                    {
                        "probe_id": "probe-h-prompt",
                        "status": "completed",
                        "probe_job_id": "job-probe-h-prompt",
                        "evidence_ids": ["job-probe-h-prompt:success"],
                    }
                ],
                "verified_root_causes": [
                    {
                        "hypothesis_id": "h-prompt",
                        "probe_id": "probe-h-prompt",
                        "summary": "Prompt patch improved success rate with locked source runner.",
                    }
                ],
            },
            "writeback": {"status_label": "待写回"},
            "action_queue": {"summary": {"total": 1, "pending": 1}},
        },
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
    assert "**统一状态视图**：Debug 任务已完成" in content
    assert "**下一步**：确认报告后执行写回。" in content
    assert "**循环探索**：第 1 轮 / verified_root_cause_found" in content
    assert "**循环下一步**：查看已验证根因并决定是否同步报告。" in content
    assert "**假设闭环**：已完成" in content
    assert "**候选假设**：1 个，已验证根因 1 个，未验证 0 个" in content
    assert "**Probe 结果**：1 个，已完成 1 个" in content
    assert "**已验证根因**：h-prompt / probe-h-prompt" in content
    assert "**公平性锁**：locked_source" in content
    assert "**写回**：待写回" in content


def _create_job_with_runtime_state() -> str:
    job_id = f"job-run-view-{uuid4()}"
    case = DebugCase.model_validate(
        {
            "case_id": f"case-run-view-{uuid4()}",
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
                raw_output='{"conflicts":[]}',
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="attribution",
        status="completed",
        input={"agent_role": "report_root_cause"},
        output={
            "meta_agent_enrichment": {
                "agent_traces": [
                    {
                        "agent_role": "report_root_cause",
                        "input_summary": {"job_id": job_id},
                        "output_summary": {"root_cause": "model_instability"},
                        "reasoning_summary": "多轮复测显示模型时序输出不稳定。",
                    }
                ],
                "recommended_actions": [
                    {
                        "category": "prompt",
                        "priority": "P0",
                        "summary": "补充视频时间窗约束后重跑验证。",
                        "detail": "把 2s-4s 时间窗写入 prompt。",
                    }
                ],
            }
        },
        failure_reason="",
        retryable=False,
    )
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="completed",
        input={"actor": "auto-debug-agent"},
        output={"summary": "auto closure completed"},
        failure_reason="",
        retryable=False,
    )
    verification_job_id = f"{job_id}__action_verify__{uuid4().hex}"
    routes.job_repository.create_job(job_id=verification_job_id, case_id=case.case_id)
    routes.job_repository.save_evidence(
        job_id=verification_job_id,
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id=f"{verification_job_id}:verify",
                step_name="recommended_action_verification",
                trial=0,
                raw_output='{"conflicts":[]}',
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    routes.job_repository.mark_completed(verification_job_id)
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
    routes.job_repository.mark_completed(job_id)
    return job_id


def _save_hypothesis_closure_stage(job_id: str) -> None:
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="hypothesis",
        status="completed",
        input={"job_id": job_id},
        output={
            "hypothesis_closure": {
                "hypotheses": [
                    {
                        "hypothesis_id": "h-prompt",
                        "category": "prompt_constraint",
                        "claim": "原 prompt 没有强制要求描述右臂和双臂配合。",
                        "supporting_evidence_ids": [f"{job_id}:image-only"],
                        "missing_evidence": ["prompt patch probe 尚未执行"],
                        "confidence_before_probe": "low",
                        "status": "candidate",
                    }
                ],
                "probe_plans": [
                    {
                        "probe_id": "probe-h-prompt",
                        "hypothesis_id": "h-prompt",
                        "intervention_type": "prompt_patch",
                        "intervention_payload": {
                            "patch": "要求逐条说明首个拿起物品的手臂。",
                        },
                        "model_runner_config_ref": "locked_source",
                        "trials": 5,
                        "success_criteria": {"required_terms": ["右臂", "双臂配合"]},
                        "stop_condition": "5 trials completed",
                    }
                ],
                "probe_results": [
                    {
                        "probe_id": "probe-h-prompt",
                        "hypothesis_id": "h-prompt",
                        "status": "not_run",
                        "source_job_id": job_id,
                        "probe_job_id": "",
                        "evidence_ids": [],
                        "summary": "controlled probe not executed yet",
                        "model_runner_config_snapshot": {},
                    }
                ],
                "causal_comparisons": [
                    {
                        "hypothesis_id": "h-prompt",
                        "probe_id": "probe-h-prompt",
                        "baseline_success_rate": 0,
                        "intervention_success_rate": 0,
                        "delta": 0,
                        "verdict": "inconclusive",
                        "evidence_summary": "controlled probe not executed yet",
                    }
                ],
                "verified_root_causes": [],
                "unverified_hypotheses": [
                    {
                        "hypothesis_id": "h-prompt",
                        "status": "candidate",
                        "summary": "原 prompt 没有强制要求描述右臂和双臂配合。",
                    }
                ],
                "fairness_lock": {"model_runner_config_ref": "locked_source"},
            }
        },
        failure_reason="",
        retryable=False,
    )


def _save_debug_loop_stage(job_id: str) -> None:
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="debug_loop",
        status="waiting",
        input={"job_id": job_id},
        output={
            "debug_loop": {
                "current_iteration": 1,
                "decision": "waiting_for_probe_completion",
                "next_action": "等待 queued probe job 完成后回流证据并重新进行因果比较。",
                "stop_reason": "",
                "iterations": [
                    {
                        "iteration": 1,
                        "source_job_id": job_id,
                        "hypothesis_count": 1,
                        "probe_plan_count": 1,
                        "probe_result_count": 1,
                        "completed_probe_count": 0,
                        "pending_probe_count": 1,
                        "causal_comparison_count": 0,
                        "supported_count": 0,
                        "decision": "waiting_for_probe_completion",
                        "next_action": "等待 queued probe job 完成后回流证据并重新进行因果比较。",
                        "stop_reason": "",
                        "probe_results": [
                            {
                                "probe_id": "probe-h1",
                                "hypothesis_id": "h1",
                                "probe_job_id": "probe-job-1",
                                "status": "not_run",
                            }
                        ],
                    }
                ],
            }
        },
        failure_reason="",
        retryable=True,
    )

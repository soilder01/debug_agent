from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.api.routes import job_repository
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_observability_summary_reports_runtime_and_operational_counts() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 2.0, "enforce_usage_budget": False})
        created = client.post("/cases/handwrite233/debug-jobs").json()
        failed = client.post("/cases/handwrite233/debug-jobs").json()
        job_repository.mark_failed(failed["job_id"], "forced failure for observability test")
        job_repository.save_spreadsheet_writeback_audit(
            job_id=failed["job_id"],
            status="failed",
            row_id="7",
            report_url=f"https://debug-agent.local/jobs/{failed['job_id']}/report",
            fields={},
            error_message="permission denied",
        )
        job_repository.save_evidence(
            job_id=failed["job_id"],
            case_id=failed["case_id"],
            evidence=[
                ExperimentEvidence(
                    evidence_id="observability-evidence-1",
                    step_name="baseline_replay",
                    trial=0,
                    request_summary={"prompt_length": 120, "has_image": True},
                    latency_ms=120,
                    response_parse_error="",
                    model_call_error_type="",
                    raw_output="{}",
                    judge=JudgeResult(score=0, reasons=["wrong answer"]),
                ),
                ExperimentEvidence(
                    evidence_id="observability-evidence-2",
                    step_name="localized_observation",
                    trial=1,
                    request_summary={"prompt_length": 80, "has_image": True},
                    latency_ms=80,
                    response_parse_error="invalid json",
                    model_call_error_type="TimeoutError",
                    model_call_error_message="request timed out",
                    raw_output="not-json",
                    judge=JudgeResult(score=0, reasons=["model_call_error"]),
                ),
            ],
        )
        strategy_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "observability-strategy-case"})
        job_repository.save_case(strategy_case)
        job_repository.create_job(job_id="observability-source", case_id=strategy_case.case_id, baseline_trials=1)
        job_repository.create_job(
            job_id="observability-strategy-follow-up",
            case_id=strategy_case.case_id,
            baseline_trials=1,
        )
        job_repository.save_evidence(
            job_id="observability-strategy-follow-up",
            case_id=strategy_case.case_id,
            evidence=[
                ExperimentEvidence(
                    evidence_id="observability-strategy-fail",
                    step_name="strategy_ablation_expansion_probe",
                    trial=0,
                    raw_output=strategy_case.predictions[0].raw_output,
                    judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
                )
            ],
        )
        job_repository.mark_completed("observability-strategy-follow-up")
        job_repository.save_strategy_follow_up_job(
            source_job_id="observability-source",
            stage="ablation_expansion",
            planned_steps="strategy_ablation_expansion_probe",
            follow_up_job_id="observability-strategy-follow-up",
            actor="strategy-operator",
            note="observe needs escalation",
        )
        targeted_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "observability-targeted-case"})
        job_repository.save_case(targeted_case)
        job_repository.create_job(job_id="observability-targeted-source", case_id=targeted_case.case_id, baseline_trials=1)
        parent_probe_job_id = ""
        for index in range(3):
            probe_job_id = f"observability-targeted-probe-{index + 1}"
            job_repository.create_job(
                job_id=probe_job_id,
                case_id=targeted_case.case_id,
                baseline_trials=1,
            )
            job_repository.save_evidence(
                job_id=probe_job_id,
                case_id=targeted_case.case_id,
                evidence=[
                    ExperimentEvidence(
                        evidence_id=f"observability-targeted-fail-{index + 1}",
                        step_name="targeted_image_region_probe",
                        trial=0,
                        raw_output=targeted_case.predictions[0].raw_output,
                        judge=JudgeResult(score=0, reasons=["image:region:1 region_label_mismatch"]),
                    )
                ],
            )
            job_repository.mark_completed(probe_job_id)
            job_repository.save_targeted_probe_job(
                source_job_id="observability-targeted-source",
                target_id="image:region:1",
                planned_steps="targeted_image_region_probe",
                probe_job_id=probe_job_id,
                source="targeted_probe" if index == 0 else "targeted_probe_outcome",
                parent_probe_job_id=parent_probe_job_id,
                trigger_outcome="" if index == 0 else "target_still_failing",
                actor="targeted-operator",
                note="observe target failure",
            )
            parent_probe_job_id = probe_job_id
        routes.settings = routes.settings.model_copy(update={"enforce_usage_budget": True})

        response = client.get("/observability/summary")

        assert response.status_code == 200
        body = response.json()
        assert body["jobs"]["total_count"] >= 2
        assert body["jobs"]["by_status"]["created"] >= 1
        assert body["jobs"]["by_status"]["failed"] >= 1
        assert body["jobs"]["pending_count"] == body["jobs"]["by_status"]["created"]
        assert body["jobs"]["failed_count"] == body["jobs"]["by_status"]["failed"]
        assert body["writeback_audits"]["total_count"] >= 1
        assert body["writeback_audits"]["by_status"]["failed"] >= 1
        assert body["evidence"]["total_evidence"] >= 2
        assert body["evidence"]["failed_judgements"] >= 2
        assert body["evidence"]["response_parse_errors"] >= 1
        assert body["evidence"]["model_call_errors"] >= 1
        assert body["evidence"]["average_latency_ms"] >= 0
        assert body["usage"]["model_call_count"] >= 2
        assert body["usage"]["prompt_character_count"] >= 200
        assert body["usage"]["estimated_cost_units"] >= 2.0
        assert body["usage"]["budget_units"] == 2.0
        assert body["usage"]["budget_status"] == "over_budget"
        assert body["usage"]["budget_utilization"] >= 1.0
        assert body["usage"]["budget_enforcement_enabled"] is True
        assert body["strategy_feedback"]["total_follow_ups"] >= 1
        assert body["strategy_feedback"]["needs_escalation_count"] >= 1
        assert body["strategy_feedback"]["pending_count"] >= 0
        assert body["strategy_feedback"]["passed_stop_condition_count"] >= 0
        assert body["targeted_probe_feedback"]["total_probes"] >= 1
        assert body["targeted_probe_feedback"]["target_still_failing_count"] >= 1
        assert body["targeted_probe_feedback"]["pending_count"] >= 0
        assert body["targeted_probe_feedback"]["target_cleared_count"] >= 0
        assert body["targeted_probe_feedback"]["inconclusive_count"] >= 0
        assert body["targeted_probe_feedback"]["max_depth_reached_count"] >= 1
        assert body["worker"]["running"] is False
        assert body["worker"]["auto_writeback_enabled"] is False
        assert body["worker"]["completion_hook_enabled"] is False
        assert body["health"]["level"] == "critical"
        assert "failed jobs present" in body["health"]["reasons"]
        assert "failed spreadsheet writebacks present" in body["health"]["reasons"]
        assert "model call errors present" in body["health"]["reasons"]
        assert "usage budget exceeded" in body["health"]["reasons"]
        assert "strategy follow-ups need escalation" in body["health"]["reasons"]
        assert "targeted probes still failing" in body["health"]["reasons"]
        assert "targeted probe guardrails reached" in body["health"]["reasons"]
        assert "Inspect failed jobs and open their evidence chain." in body["health"]["actions"]
        assert "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers." in body["health"][
            "actions"
        ]
        assert "Check model endpoint health, timeout settings, and retry affected jobs." in body["health"]["actions"]
        assert "Pause new submissions or raise the usage budget before continuing." in body["health"]["actions"]
        assert "Open strategy follow-up history and run escalation probes." in body["health"]["actions"]
        assert "Open targeted probe history and escalate unresolved targets." in body["health"]["actions"]
        assert "Review targeted probe guardrails and assign human investigation." in body["health"]["actions"]

        job_repository.mark_failed(created["job_id"], "test cleanup")
    finally:
        routes.settings = original_settings

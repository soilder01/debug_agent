import time
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.api.schemas import SpreadsheetRerunAutoClosureReport
from debug_agent.cases.models import DebugCase
from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.main import app
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def test_worker_status_endpoint_reports_lifecycle_state() -> None:
    client = TestClient(app)

    response = client.get("/worker/status")

    assert response.status_code == 200
    assert response.json() == {
        "running": False,
        "max_concurrency": 1,
        "active_count": 0,
        "processed_count": 0,
        "error_count": 0,
        "recovered_stale_job_count": 0,
        "last_error": None,
        "completion_hook_enabled": False,
        "report_base_url": "http://localhost:8000",
        "auto_writeback_enabled": False,
    }


def test_worker_start_is_idempotent_and_stop_updates_status() -> None:
    client = TestClient(app)

    first_start = client.post("/worker/start")
    second_start = client.post("/worker/start")
    stop_response = client.post("/worker/stop")
    status_response = client.get("/worker/status")

    assert first_start.status_code == 202
    assert first_start.json()["running"] is True
    assert second_start.status_code == 202
    assert second_start.json()["running"] is True
    assert stop_response.status_code == 200
    assert stop_response.json()["running"] is False
    assert status_response.json()["running"] is False


def _fake_model_provider(case):
    return FakeModelAdapter([prediction.raw_output for prediction in case.predictions])


def _minimal_debug_case(case_id: str, raw_output: str) -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": case_id,
            "task_type": "generic_video_json",
            "image_uri": "file:///tmp/worker-controlled.mp4",
            "prompt": "Return JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {"answer": "fixed"},
            "scoring_standard": "answer must be fixed.",
            "predictions": [{"trial": 0, "raw_output": raw_output, "score": 1}],
            "avg_score": 1,
        }
    )


def test_worker_start_consumes_submitted_debug_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes.job_service, "_model_provider", _fake_model_provider)
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs")
    job_id = submit_response.json()["job_id"]

    start_response = client.post("/worker/start")
    wait_until(
        lambda: (
            (status := client.get(f"/jobs/{job_id}").json())["status"] == "completed"
            and len(status["evidence_ids"]) == 6
        )
    )
    stop_response = client.post("/worker/stop")

    status_response = client.get(f"/jobs/{job_id}")
    worker_status = client.get("/worker/status").json()
    assert start_response.status_code == 202
    assert stop_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["attempt_count"] == 1
    assert len(status_response.json()["evidence_ids"]) == 6
    assert worker_status["processed_count"] >= 1


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.row_id = ""
        self.fields: dict[str, str] = {}

    def update_row(
        self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]
    ) -> None:
        self.row_id = row_id
        self.fields = fields


@pytest.mark.asyncio
async def test_runtime_worker_writes_report_back_after_completed_mapped_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    submitted = service.submit_case_debug("handwrite233", baseline_trials=1)
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        case_id=submitted.case_id,
        job_id=submitted.job_id,
    )
    writeback_client = RecordingWritebackClient()
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=writeback_client,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=True,
        auto_closure_enabled=False,
    )

    assert worker.status().completion_hook_enabled is True

    await worker.tick()

    assert writeback_client.row_id == "7"
    assert (
        writeback_client.fields["分析报告链接"]
        == f"https://debug-agent.local/jobs/{submitted.job_id}/report"
    )
    assert writeback_client.fields["错误原因"]
    assert worker.status().error_count == 0


@pytest.mark.asyncio
async def test_runtime_worker_runs_auto_closure_after_root_job_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    submitted = service.submit_case_debug("handwrite233", baseline_trials=1)
    calls: list[str] = []

    async def fake_run_auto_debug_closure(**kwargs):
        calls.append(kwargs["job_id"])
        return AutoDebugClosureResult(
            source_job_id=kwargs["job_id"],
            created_targeted_probe_jobs=["probe-job-1"],
            created_verification_jobs=["verify-job-1"],
            final_attribution_candidates=[{"category": "model_instability"}],
        )

    monkeypatch.setattr(routes, "run_auto_debug_closure", fake_run_auto_debug_closure)
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )

    assert worker.status().completion_hook_enabled is True

    await worker.tick()

    assert calls == [submitted.job_id]
    stages = repository.list_debug_run_stages(submitted.job_id)
    assert any(stage.stage == "targeted" and stage.status == "completed" for stage in stages)
    assert any(stage.stage == "verification" and stage.status == "completed" for stage in stages)


@pytest.mark.asyncio
async def test_runtime_worker_passes_batch_controlled_probe_opt_in_to_auto_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    batch_id = "async-dogfood-controlled-probe"
    repository.create_batch(
        batch_id=batch_id,
        total_jobs=1,
        retry_policy={"source": "spreadsheet_rerun", "submit_controlled_probes": True},
    )
    submitted = service.submit_case_debug(
        "handwrite233", baseline_trials=1, artifact_group_id=batch_id
    )
    calls: list[dict[str, object]] = []

    async def fake_run_auto_debug_closure(**kwargs):
        calls.append(kwargs)
        return AutoDebugClosureResult(source_job_id=kwargs["job_id"])

    monkeypatch.setattr(routes, "run_auto_debug_closure", fake_run_auto_debug_closure)
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )

    await worker.tick()

    assert calls
    assert calls[0]["job_id"] == submitted.job_id
    assert calls[0]["submit_controlled_probes"] is True


@pytest.mark.asyncio
async def test_runtime_worker_reruns_source_auto_closure_after_controlled_probe_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    source_case = _minimal_debug_case("worker-controlled-source", "{}")
    probe_case = _minimal_debug_case(
        "worker-controlled-source__hypothesis_probe__probe_h_prompt",
        '{"answer":"fixed"}',
    )
    repository.save_case(source_case)
    repository.save_case(probe_case)
    source_job_id = "worker-controlled-source-job"
    probe_job_id = "worker-controlled-probe-job"
    repository.create_job(source_job_id, source_case.case_id, baseline_trials=1)
    repository.mark_completed(source_job_id)
    repository.create_job(probe_job_id, probe_case.case_id, baseline_trials=1)
    repository.save_debug_run_stage(
        job_id=source_job_id,
        stage="hypothesis",
        status="completed",
        input={"job_id": source_job_id},
        output={
            "hypothesis_closure": {
                "probe_results": [
                    {
                        "probe_id": "probe-h-prompt",
                        "hypothesis_id": "h-prompt",
                        "status": "not_run",
                        "source_job_id": source_job_id,
                        "probe_job_id": probe_job_id,
                        "evidence_ids": [],
                        "model_runner_config_snapshot": {
                            "locked": True,
                            "mode": "high",
                            "thinking": "disabled",
                        },
                    }
                ]
            }
        },
        failure_reason="",
        retryable=False,
    )
    service = DebugJobService(repository, model_provider=_fake_model_provider)
    calls: list[str] = []

    async def fake_run_auto_debug_closure(**kwargs):
        calls.append(kwargs["job_id"])
        return AutoDebugClosureResult(source_job_id=kwargs["job_id"])

    monkeypatch.setattr(routes, "run_auto_debug_closure", fake_run_auto_debug_closure)
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )

    await worker.tick()

    assert repository.get_job(probe_job_id).status == "completed"
    assert calls == [source_job_id]
    assert not any(
        stage.stage == "auto_closure" for stage in repository.list_debug_run_stages(probe_job_id)
    )


@pytest.mark.asyncio
async def test_runtime_worker_records_async_spreadsheet_report_and_writeback_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    batch_id = "async-dogfood-report-batch"
    command_id = "async-dogfood-report-command"
    repository.create_batch(
        batch_id=batch_id,
        total_jobs=1,
        retry_policy={
            "source": "spreadsheet_rerun",
            "auto_closure": True,
            "writeback": True,
            "submit_controlled_probes": True,
        },
    )
    submitted = service.submit_case_debug(
        "handwrite233", baseline_trials=1, artifact_group_id=batch_id
    )
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-async",
        sheet_id="sheet-async",
        row_id="2",
        case_id=submitted.case_id,
        job_id=submitted.job_id,
    )
    repository.create_lark_bot_pending_command(
        command_id=command_id,
        actor="ou_async_report",
        open_id="ou_async_report",
        chat_id="oc_async_report",
        message_id="om_async_report",
        tenant_key="tenant-async-report",
        identity="bot",
        profile="debug-bot",
        command_text="/debug spreadsheet rerun --report --writeback",
        action_kind="spreadsheet_rerun",
        action={"kind": "spreadsheet_rerun", "parameters": {}},
        card={},
        note="test",
        expires_at="2099-01-01T00:00:00+00:00",
    )
    repository.create_xiaod_execution_run(
        run_id="run-async-report",
        tenant_key="tenant-async-report",
        chat_id="oc_async_report",
        open_id="ou_async_report",
        command_id=command_id,
        batch_id=batch_id,
        action_kind="spreadsheet_rerun",
        status="active",
        summary={
            "command_id": command_id,
            "batch_id": batch_id,
            "job_ids": [submitted.job_id],
            "report_requested": True,
            "writeback_requested": True,
            "writeback_decision_status": "not_ready",
        },
    )
    calls: list[dict[str, object]] = []

    async def fake_run_report_for_completed_job(
        job_id: str,
        *,
        writeback_requested: bool,
        submit_controlled_probes: bool = False,
        execute_follow_up_jobs: bool = True,
    ) -> SpreadsheetRerunAutoClosureReport:
        calls.append(
            {
                "job_id": job_id,
                "writeback_requested": writeback_requested,
                "submit_controlled_probes": submit_controlled_probes,
                "execute_follow_up_jobs": execute_follow_up_jobs,
            }
        )
        return SpreadsheetRerunAutoClosureReport(
            job_id=job_id,
            case_id=submitted.case_id,
            closure=AutoDebugClosureResult(source_job_id=job_id),
            report_artifact_url=f"/api/artifacts/files/{job_id}_auto_closure_report.md",
            writeback_status="sync_decision_pending",
        )

    monkeypatch.setattr(
        routes.auto_closure_report_controller,
        "run_report_for_completed_job",
        fake_run_report_for_completed_job,
    )
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )

    await worker.tick()

    assert calls == [
        {
            "job_id": submitted.job_id,
            "writeback_requested": True,
            "submit_controlled_probes": True,
            "execute_follow_up_jobs": False,
        }
    ]
    run = next(
        item
        for item in repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == "run-async-report"
    )
    assert run.status == "writeback_decision_pending"
    assert run.summary["report_count"] == 1
    assert run.summary["writeback_decision_status"] == "pending"
    assert run.summary["row_results"][0]["row_id"] == "2"
    assert run.summary["row_results"][0]["report_url"].endswith(
        f"/jobs/{submitted.job_id}/report"
    )
    decision = repository.get_pending_xiaod_decision(
        tenant_key="tenant-async-report",
        chat_id="oc_async_report",
        open_id="ou_async_report",
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    assert decision is not None
    assert decision.command_id == command_id


@pytest.mark.asyncio
async def test_runtime_worker_skips_auto_closure_for_auto_generated_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    submitted = service.submit_case_debug("handwrite233", baseline_trials=1)
    repository.save_strategy_follow_up_job(
        source_job_id="root-job",
        stage="stability_verification",
        planned_steps="stability_verification_probe",
        follow_up_job_id=submitted.job_id,
    )
    calls: list[str] = []

    async def fake_run_auto_debug_closure(**kwargs):
        calls.append(kwargs["job_id"])
        return AutoDebugClosureResult(source_job_id=kwargs["job_id"])

    monkeypatch.setattr(routes, "run_auto_debug_closure", fake_run_auto_debug_closure)
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )

    await worker.tick()

    assert calls == []


def test_runtime_worker_leaves_completion_hook_disabled_when_auto_writeback_is_off() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository, model_provider=_fake_model_provider, enable_fixture_fallback=True
    )
    writeback_client = RecordingWritebackClient()

    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=writeback_client,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=False,
    )

    assert worker.status().completion_hook_enabled is False

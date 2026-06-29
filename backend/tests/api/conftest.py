# ruff: noqa: E402
import asyncio
import os
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_API_TEST_RUNTIME_PATH = _PROJECT_ROOT / ".tmp" / f"api-tests-{os.getpid()}"
_API_TEST_RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
_PREVIOUS_DATABASE_URL = os.environ.get("DEBUG_AGENT_DATABASE_URL")
_PREVIOUS_IMAGE_ARTIFACT_DIR = os.environ.get("DEBUG_AGENT_IMAGE_ARTIFACT_DIR")
_PREVIOUS_LARK_REPORT_DOCS_ENABLED = os.environ.get("LARK_REPORT_DOCS_ENABLED")
os.environ["DEBUG_AGENT_DATABASE_URL"] = (
    f"sqlite+pysqlite:///{(_API_TEST_RUNTIME_PATH / 'debug-agent-api-tests.db').as_posix()}"
)
os.environ["DEBUG_AGENT_IMAGE_ARTIFACT_DIR"] = str(_API_TEST_RUNTIME_PATH / "artifacts")
os.environ["LARK_REPORT_DOCS_ENABLED"] = "0"

from debug_agent.api import routes
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.models import Base

if _PREVIOUS_DATABASE_URL is None:
    os.environ.pop("DEBUG_AGENT_DATABASE_URL", None)
else:
    os.environ["DEBUG_AGENT_DATABASE_URL"] = _PREVIOUS_DATABASE_URL
if _PREVIOUS_IMAGE_ARTIFACT_DIR is None:
    os.environ.pop("DEBUG_AGENT_IMAGE_ARTIFACT_DIR", None)
else:
    os.environ["DEBUG_AGENT_IMAGE_ARTIFACT_DIR"] = _PREVIOUS_IMAGE_ARTIFACT_DIR
if _PREVIOUS_LARK_REPORT_DOCS_ENABLED is None:
    os.environ.pop("LARK_REPORT_DOCS_ENABLED", None)
else:
    os.environ["LARK_REPORT_DOCS_ENABLED"] = _PREVIOUS_LARK_REPORT_DOCS_ENABLED


def _fake_model_provider(case):
    return FakeModelAdapter([prediction.raw_output for prediction in case.predictions])


@pytest.fixture(autouse=True)
def isolate_api_route_state() -> None:
    original_semantic_brain = routes.xiaod_semantic_brain
    _stop_worker_if_running()
    _clear_database()
    routes.xiaod_semantic_brain = None
    routes.job_service._model_provider = _fake_model_provider
    routes.job_worker = AsyncJobWorker(
        routes.job_service, max_concurrency=routes.settings.queue_max_concurrency
    )
    routes.spreadsheet_sync_client = None
    routes.spreadsheet_writeback_client = None
    routes.job_repository.save_case(load_fixture_case("handwrite233"))
    yield
    _stop_worker_if_running()
    routes.job_service._model_provider = None
    routes.job_worker = AsyncJobWorker(
        routes.job_service, max_concurrency=routes.settings.queue_max_concurrency
    )
    routes.xiaod_semantic_brain = original_semantic_brain
    routes.spreadsheet_sync_client = None
    routes.spreadsheet_writeback_client = None
    _clear_database()
    routes.job_repository.save_case(load_fixture_case("handwrite233"))


def _clear_database() -> None:
    with routes.engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def _stop_worker_if_running() -> None:
    if routes.job_worker.status().running:
        asyncio.run(routes.job_worker.stop())

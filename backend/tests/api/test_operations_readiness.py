import io
import json
import os
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkSpreadsheetReference


def test_operations_readiness_reports_runtime_config_and_checks() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "environment": "pilot",
                "lark_event_mode": "webhook",
                "report_base_url": "https://debug-agent.local",
                "usage_budget_units": 50.0,
                "enforce_usage_budget": True,
                "require_trusted_actor": True,
                "lark_bot_verification_token": SecretStr("bot-token"),
                "lark_bot_encrypt_key": SecretStr("encrypt-key"),
            }
        )
        routes.lark_spreadsheet_settings = LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/spreadsheet-1?sheet=sheet-1",
            sheet_id="sheet-1",
            lark_cli_profile="debug-bot",
            lark_cli_identity="bot",
            reference=LarkSpreadsheetReference(spreadsheet_id="spreadsheet-1", sheet_id="sheet-1"),
        )

        response = client.get("/api/operations/readiness")

        assert response.status_code == 200
        body = response.json()
        assert body["generated_at"]
        assert body["level"] in {"healthy", "degraded", "critical"}
        assert body["config"]["environment"] == "pilot"
        assert body["config"]["database_url"].startswith("sqlite")
        assert body["config"]["artifact_root"]
        assert (
            body["config"]["artifact_retention_days"] == original_settings.artifact_retention_days
        )
        assert body["config"]["report_base_url"] == "https://debug-agent.local"
        assert body["config"]["usage_budget_units"] == 50.0
        assert body["config"]["enforce_usage_budget"] is True
        assert body["config"]["require_trusted_actor"] is True
        assert body["config"]["lark_configured"] is True
        assert body["config"]["lark_event_mode"] == "webhook"
        assert body["config"]["lark_bot_verification_configured"] is True
        assert body["config"]["lark_bot_encrypt_configured"] is True
        assert {path["name"] for path in body["paths"]} >= {"artifact_root", "run_artifacts"}
        check_keys = {check["key"] for check in body["checks"]}
        assert "database" in check_keys
        assert "report_base_url" in check_keys
        assert "trusted_actor" in check_keys
        assert "lark_bot_webhook_token" in check_keys
        assert "lark_bot_encrypt_key" in check_keys
        assert body["export_urls"]["readiness"] == "/api/operations/readiness"
        assert body["export_urls"]["performance"] == "/api/performance/summary"
        assert body["export_urls"]["artifact_retention"] == "/api/operations/artifact-retention"
        assert (
            body["export_urls"]["artifact_retention_cleanup"]
            == "/api/operations/artifact-retention/cleanup"
        )
        assert body["export_urls"]["database_backup"] == "/api/operations/database-backup.zip"
        assert (
            body["export_urls"]["operations_support_bundle"] == "/api/operations/support-bundle.zip"
        )
        assert body["export_urls"]["lark_bot_preflight"] == "/api/lark/bot/preflight"
        assert body["export_urls"]["lark_bot_go_live_gate"] == "/api/lark/bot/go-live-gate"
        assert (
            body["export_urls"]["lark_bot_permission_checklist"]
            == "/api/lark/bot/permission-checklist"
        )
        assert body["export_urls"]["lark_bot_setup_package"] == "/api/lark/bot/setup-package.zip"
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_operations_support_bundle_exports_redacted_runtime_files() -> None:
    client = TestClient(app)

    response = client.get("/api/operations/support-bundle.zip?audit_limit=5")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "manifest.json",
            "README.txt",
            "readiness.json",
            "observability_summary.json",
            "performance_summary.json",
            "worker_status.json",
            "artifact_retention.json",
            "pilot_gate.json",
            "lark_bot_preflight.json",
            "lark_bot_go_live_gate.json",
            "lark_bot_permission_checklist.json",
            "lark_bot_setup_acknowledgements.json",
            "lark_operation_audits.json",
            "spreadsheet_writeback_audits.json",
        } <= names
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        readiness = json.loads(archive.read("readiness.json").decode("utf-8"))
        pilot_gate = json.loads(archive.read("pilot_gate.json").decode("utf-8"))
        assert manifest["export_type"] == "operations_support_bundle"
        assert manifest["audit_limit"] == 5
        assert "credentials" in manifest["redaction"]
        assert readiness["config"]["database_url"]
        assert "checks" in pilot_gate
        assert "app_secret" not in response.content.decode("utf-8", errors="ignore").lower()


def test_artifact_retention_status_reports_dry_run_candidates(tmp_path: Path) -> None:
    client = TestClient(app)
    original_settings = routes.settings
    runs_dir = tmp_path / "runs" / "batch-1" / "job-1"
    runs_dir.mkdir(parents=True)
    old_file = runs_dir / "old.txt"
    fresh_file = runs_dir / "fresh.txt"
    old_file.write_text("old artifact", encoding="utf-8")
    fresh_file.write_text("fresh artifact", encoding="utf-8")
    old_timestamp = (datetime.now(UTC) - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_timestamp, old_timestamp))
    try:
        routes.settings = original_settings.model_copy(
            update={
                "image_artifact_dir": tmp_path,
                "artifact_retention_days": 7,
            }
        )

        response = client.get("/api/operations/artifact-retention?limit=1")

        assert response.status_code == 200
        body = response.json()
        assert body["artifact_root"] == str(tmp_path.resolve())
        assert body["retention_days"] == 7
        assert body["total_file_count"] == 2
        assert body["eligible_file_count"] == 1
        assert body["eligible_size_bytes"] == len("old artifact")
        assert body["eligible_samples"][0]["relative_path"].endswith("old.txt")
        assert "干跑" in body["action"]
    finally:
        routes.settings = original_settings


def test_artifact_retention_cleanup_requires_confirmation_and_deletes_only_expired_files(
    tmp_path: Path,
) -> None:
    client = TestClient(app)
    original_settings = routes.settings
    runs_dir = tmp_path / "runs" / "batch-1" / "job-1"
    runs_dir.mkdir(parents=True)
    old_file = runs_dir / "old.txt"
    fresh_file = runs_dir / "fresh.txt"
    old_file.write_text("old artifact", encoding="utf-8")
    fresh_file.write_text("fresh artifact", encoding="utf-8")
    old_timestamp = (datetime.now(UTC) - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_timestamp, old_timestamp))
    try:
        routes.settings = original_settings.model_copy(
            update={
                "image_artifact_dir": tmp_path,
                "artifact_retention_days": 7,
            }
        )

        dry_run = client.post(
            "/api/operations/artifact-retention/cleanup",
            json={"actor": "ops-reviewer", "dry_run": True, "limit": 10},
        )
        rejected = client.post(
            "/api/operations/artifact-retention/cleanup",
            json={"actor": "ops-reviewer", "dry_run": False, "limit": 10},
        )

        assert dry_run.status_code == 200
        assert dry_run.json()["deleted_file_count"] == 0
        assert old_file.exists()
        assert rejected.status_code == 400
        assert old_file.exists()
        confirmed = client.post(
            "/api/operations/artifact-retention/cleanup",
            json={
                "actor": "ops-reviewer",
                "dry_run": False,
                "confirmation": "DELETE_EXPIRED_ARTIFACTS",
                "limit": 10,
            },
        )

        assert confirmed.status_code == 200
        body = confirmed.json()
        assert body["actor"] == "ops-reviewer"
        assert body["dry_run"] is False
        assert body["deleted_file_count"] == 1
        assert body["deleted_size_bytes"] == len("old artifact")
        assert not old_file.exists()
        assert fresh_file.exists()
        assert body["status_after"]["eligible_file_count"] == 0
    finally:
        routes.settings = original_settings


def test_database_backup_exports_sqlite_database_file(tmp_path: Path) -> None:
    client = TestClient(app)
    original_settings = routes.settings
    database_path = tmp_path / "debug-agent.db"
    wal_path = tmp_path / "debug-agent.db-wal"
    database_path.write_bytes(b"sqlite database bytes")
    wal_path.write_bytes(b"wal bytes")
    try:
        routes.settings = original_settings.model_copy(
            update={"database_url": f"sqlite+pysqlite:///{database_path.as_posix()}"}
        )

        response = client.get("/api/operations/database-backup.zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            assert "manifest.json" in names
            assert "database/debug-agent.db" in names
            assert "database/debug-agent.db-wal" in names
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            assert manifest["export_type"] == "database_backup"
            assert manifest["database_kind"] == "sqlite"
            assert manifest["file_count"] == 2
            assert archive.read("database/debug-agent.db") == b"sqlite database bytes"
    finally:
        routes.settings = original_settings

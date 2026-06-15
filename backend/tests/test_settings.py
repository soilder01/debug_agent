from pathlib import Path

from debug_agent.settings import ArkSettings, DebugAgentSettings, LarkSpreadsheetSettings, load_env_file


def test_debug_agent_settings_default_to_in_memory_database(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_DATABASE_URL", raising=False)

    settings = DebugAgentSettings.from_env()

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_debug_agent_settings_read_database_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_DATABASE_URL", "sqlite+pysqlite:///./debug_agent.db")

    settings = DebugAgentSettings.from_env()

    assert settings.database_url == "sqlite+pysqlite:///./debug_agent.db"


def test_debug_agent_settings_read_image_artifact_dir_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_IMAGE_ARTIFACT_DIR", "runtime-artifacts/crops")

    settings = DebugAgentSettings.from_env()

    assert settings.image_artifact_dir == Path("runtime-artifacts/crops")


def test_debug_agent_settings_read_report_base_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_REPORT_BASE_URL", "https://debug-agent.example")

    settings = DebugAgentSettings.from_env()

    assert settings.report_base_url == "https://debug-agent.example"


def test_debug_agent_settings_disable_auto_writeback_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_AUTO_WRITEBACK_ENABLED", raising=False)

    settings = DebugAgentSettings.from_env()

    assert settings.auto_writeback_enabled is False


def test_debug_agent_settings_read_auto_writeback_enabled_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_AUTO_WRITEBACK_ENABLED", "1")

    settings = DebugAgentSettings.from_env()

    assert settings.auto_writeback_enabled is True


def test_debug_agent_settings_read_usage_budget_units_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_USAGE_BUDGET_UNITS", "25.5")

    settings = DebugAgentSettings.from_env()

    assert settings.usage_budget_units == 25.5


def test_debug_agent_settings_do_not_enforce_usage_budget_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_ENFORCE_USAGE_BUDGET", raising=False)

    settings = DebugAgentSettings.from_env()

    assert settings.enforce_usage_budget is False


def test_debug_agent_settings_read_enforce_usage_budget_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_ENFORCE_USAGE_BUDGET", "true")

    settings = DebugAgentSettings.from_env()

    assert settings.enforce_usage_budget is True


def test_debug_agent_settings_do_not_require_trusted_actor_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR", raising=False)

    settings = DebugAgentSettings.from_env()

    assert settings.require_trusted_actor is False


def test_debug_agent_settings_read_require_trusted_actor_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR", "true")

    settings = DebugAgentSettings.from_env()

    assert settings.require_trusted_actor is True


def test_load_env_file_populates_missing_environment_values(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_MODEL_PROVIDER", raising=False)
    env_file = Path(__file__).with_name(".settings-provider-test.env")
    try:
        env_file.write_text("DEBUG_AGENT_MODEL_PROVIDER=ark-seed2-lite\n", encoding="utf-8")

        load_env_file(env_file)

        assert DebugAgentSettings.from_env().database_url == "sqlite+pysqlite:///:memory:"
        from debug_agent.settings import ModelRuntimeSettings

        assert ModelRuntimeSettings.from_env().provider == "ark-seed2-lite"
    finally:
        env_file.unlink(missing_ok=True)


def test_ark_settings_can_be_built_from_env_file(monkeypatch) -> None:
    for key in (
        "ARK_API_KEY",
        "ARK_BASE_URL",
        "ARK_CONTENT_TASKS_URL",
        "ARK_SEED2_LITE_MODEL_ID",
        "ARK_SEED2_PRO_MODEL_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    env_file = Path(__file__).with_name(".settings-ark-test.env")
    try:
        env_file.write_text(
            "\n".join(
                [
                    "ARK_API_KEY=secret-value",
                    "ARK_BASE_URL=https://ark.example/api/v3",
                    "ARK_CONTENT_TASKS_URL=https://ark.example/api/v3/contents/generations/tasks",
                    "ARK_SEED2_LITE_MODEL_ID=lite-model",
                    "ARK_SEED2_PRO_MODEL_ID=pro-model",
                ]
            ),
            encoding="utf-8",
        )

        load_env_file(env_file)

        settings = ArkSettings.from_env()
        assert settings.api_key.get_secret_value() == "secret-value"
        assert settings.base_url == "https://ark.example/api/v3"
        assert settings.content_tasks_url == "https://ark.example/api/v3/contents/generations/tasks"
        assert settings.seed2_lite_model_id == "lite-model"
        assert settings.seed2_pro_model_id == "pro-model"
    finally:
        env_file.unlink(missing_ok=True)


def test_lark_spreadsheet_settings_are_optional(monkeypatch) -> None:
    monkeypatch.delenv("LARK_SPREADSHEET_URL", raising=False)
    monkeypatch.delenv("LARK_SHEET_ID", raising=False)

    settings = LarkSpreadsheetSettings.from_env()

    assert settings.spreadsheet_url == ""
    assert settings.sheet_id == ""
    assert settings.reference is None


def test_lark_spreadsheet_settings_parse_default_reference(monkeypatch) -> None:
    monkeypatch.setenv(
        "LARK_SPREADSHEET_URL",
        "https://bytedance.larkoffice.com/sheets/N935sK3fzhGDiNtwT3LcRLDTnvb?sheet=wAKHdf",
    )
    monkeypatch.delenv("LARK_SHEET_ID", raising=False)

    settings = LarkSpreadsheetSettings.from_env()

    assert settings.reference is not None
    assert settings.reference.spreadsheet_id == "N935sK3fzhGDiNtwT3LcRLDTnvb"
    assert settings.reference.sheet_id == "wAKHdf"


def test_lark_spreadsheet_settings_allow_sheet_id_override(monkeypatch) -> None:
    monkeypatch.setenv("LARK_SPREADSHEET_URL", "N935sK3fzhGDiNtwT3LcRLDTnvb")
    monkeypatch.setenv("LARK_SHEET_ID", "wAKHdf")

    settings = LarkSpreadsheetSettings.from_env()

    assert settings.reference is not None
    assert settings.reference.spreadsheet_id == "N935sK3fzhGDiNtwT3LcRLDTnvb"
    assert settings.reference.sheet_id == "wAKHdf"


def test_lark_spreadsheet_settings_read_cli_timeout_from_env(monkeypatch) -> None:
    monkeypatch.delenv("LARK_SPREADSHEET_URL", raising=False)
    monkeypatch.setenv("LARK_CLI_TIMEOUT_SECONDS", "120")

    settings = LarkSpreadsheetSettings.from_env()

    assert settings.lark_cli_timeout_seconds == 120

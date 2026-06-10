from debug_agent.settings import DebugAgentSettings


def test_debug_agent_settings_default_to_in_memory_database(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG_AGENT_DATABASE_URL", raising=False)

    settings = DebugAgentSettings.from_env()

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_debug_agent_settings_read_database_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_DATABASE_URL", "sqlite+pysqlite:///./debug_agent.db")

    settings = DebugAgentSettings.from_env()

    assert settings.database_url == "sqlite+pysqlite:///./debug_agent.db"

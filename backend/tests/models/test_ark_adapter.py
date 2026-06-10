from debug_agent.settings import ArkSettings


def test_ark_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.example/api/v3")
    monkeypatch.setenv("ARK_SEED2_LITE_MODEL_ID", "lite-model")
    monkeypatch.setenv("ARK_SEED2_PRO_MODEL_ID", "pro-model")

    settings = ArkSettings.from_env()

    assert settings.api_key.get_secret_value() == "secret-value"
    assert settings.base_url == "https://ark.example/api/v3"
    assert settings.seed2_lite_model_id == "lite-model"
    assert settings.seed2_pro_model_id == "pro-model"

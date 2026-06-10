from debug_agent.settings import ArkSettings
from debug_agent.models.ark import ArkModelAdapter


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


def test_ark_adapter_builds_request_without_exposing_secret() -> None:
    settings = ArkSettings(
        api_key="secret-value",
        base_url="https://ark.example/api/v3",
        content_tasks_url="https://ark.example/api/v3/contents/generations/tasks",
        seed2_lite_model_id="lite-model",
        seed2_pro_model_id="pro-model",
    )
    adapter = ArkModelAdapter(settings=settings, model_id=settings.seed2_lite_model_id)

    request = adapter.build_request(prompt="hello", image_uri="tos://image")

    assert request.url == "https://ark.example/api/v3/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-value"
    assert request.json_body["model"] == "lite-model"
    assert "secret-value" not in repr(request)

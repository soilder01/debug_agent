import pytest

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.models.factory import build_model_adapter
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.settings import ModelRuntimeSettings


def test_model_factory_builds_fake_adapter_by_default() -> None:
    case = load_fixture_case("handwrite233")

    adapter = build_model_adapter(case, settings=ModelRuntimeSettings())

    assert isinstance(adapter, FakeModelAdapter)


def test_model_factory_builds_ark_seed2_lite_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    case = load_fixture_case("handwrite233")
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_SEED2_LITE_MODEL_ID", "lite-model")

    adapter = build_model_adapter(case, settings=ModelRuntimeSettings(provider="ark-seed2-lite"))

    assert isinstance(adapter, ArkModelAdapter)
    request = adapter.build_request(prompt="hello", image_uri="")
    assert request.json_body["model"] == "lite-model"


def test_model_factory_builds_ark_seed2_pro_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    case = load_fixture_case("handwrite233")
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_SEED2_PRO_MODEL_ID", "pro-model")

    adapter = build_model_adapter(case, settings=ModelRuntimeSettings(provider="ark-seed2-pro"))

    assert isinstance(adapter, ArkModelAdapter)
    request = adapter.build_request(prompt="hello", image_uri="")
    assert request.json_body["model"] == "pro-model"


def test_model_factory_builds_ark_video_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    case = load_fixture_case("handwrite233")
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_VIDEO_MODEL_ID", "video-model")
    monkeypatch.setenv("ARK_VIDEO_MODE", "high")
    monkeypatch.setenv("ARK_VIDEO_DISABLE_THINKING", "1")

    adapter = build_model_adapter(case, settings=ModelRuntimeSettings(provider="ark-video"))

    assert isinstance(adapter, ArkModelAdapter)
    request = adapter.build_request(prompt="hello", image_uri="https://media.example/case.mp4")
    assert request.json_body["model"] == "video-model"
    assert request.json_body["mode"] == "high"
    assert request.json_body["thinking"] == {"type": "disabled"}


def test_model_factory_rejects_unknown_provider() -> None:
    case = load_fixture_case("handwrite233")

    with pytest.raises(ValueError, match="Unsupported model provider"):
        build_model_adapter(case, settings=ModelRuntimeSettings(provider="unknown"))


def test_model_runtime_settings_reads_provider_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG_AGENT_MODEL_PROVIDER", "ark-seed2-lite")

    settings = ModelRuntimeSettings.from_env()

    assert settings.provider == "ark-seed2-lite"

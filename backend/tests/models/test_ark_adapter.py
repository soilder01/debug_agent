import pytest
from urllib.error import HTTPError
from io import BytesIO
import base64
from pathlib import Path

from debug_agent.settings import ArkSettings
from debug_agent.models.ark import ArkModelAdapter, ArkRequest, UrllibArkTransport


def test_ark_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.example/api/v3")
    monkeypatch.setenv("ARK_SEED2_LITE_MODEL_ID", "lite-model")
    monkeypatch.setenv("ARK_SEED2_PRO_MODEL_ID", "pro-model")
    monkeypatch.setenv("ARK_VIDEO_MODEL_ID", "video-model")
    monkeypatch.setenv("ARK_VIDEO_MODE", "high")
    monkeypatch.setenv("ARK_VIDEO_DISABLE_THINKING", "1")

    settings = ArkSettings.from_env()

    assert settings.api_key.get_secret_value() == "secret-value"
    assert settings.base_url == "https://ark.example/api/v3"
    assert settings.seed2_lite_model_id == "lite-model"
    assert settings.seed2_pro_model_id == "pro-model"
    assert settings.video_model_id == "video-model"
    assert settings.video_mode == "high"
    assert settings.video_disable_thinking is True


def test_ark_adapter_builds_request_without_exposing_secret() -> None:
    settings = ArkSettings(
        api_key="secret-value",
        base_url="https://ark.example/api/v3",
        content_tasks_url="https://ark.example/api/v3/contents/generations/tasks",
        seed2_lite_model_id="lite-model",
        seed2_pro_model_id="pro-model",
        video_model_id="video-model",
    )
    adapter = ArkModelAdapter(settings=settings, model_id=settings.seed2_lite_model_id)

    request = adapter.build_request(prompt="hello", image_uri="tos://image")

    assert request.url == "https://ark.example/api/v3/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-value"
    assert request.json_body["model"] == "lite-model"
    assert "secret-value" not in repr(request)


def test_ark_adapter_builds_high_no_thinking_video_request() -> None:
    settings = ark_settings()
    adapter = ArkModelAdapter(
        settings=settings,
        model_id=settings.video_model_id,
        mode=settings.video_mode,
        disable_thinking=settings.video_disable_thinking,
    )

    request = adapter.build_request(prompt="segment this video", image_uri="file:///tmp/case.mp4")

    assert request.json_body["model"] == "video-model"
    assert request.json_body["mode"] == "high"
    assert request.json_body["thinking"] == {"type": "disabled"}
    messages = request.json_body["messages"]
    assert isinstance(messages, list)
    content = messages[0]["content"]  # type: ignore[index]
    assert content[1] == {"type": "video_url", "video_url": {"url": "file:///tmp/case.mp4"}}


def test_ark_adapter_converts_local_video_file_uri_to_base64_data_url() -> None:
    video_path = Path(__file__).with_name(".ark-test-video.mp4")
    video_path.write_bytes(b"fake-video")
    adapter = ArkModelAdapter(
        settings=ark_settings(),
        model_id="video-model",
        mode="high",
        disable_thinking=True,
    )

    try:
        request = adapter.build_request(prompt="segment this video", image_uri=video_path.as_uri())
    finally:
        video_path.unlink(missing_ok=True)

    messages = request.json_body["messages"]
    assert isinstance(messages, list)
    content = messages[0]["content"]  # type: ignore[index]
    video_url = content[1]["video_url"]["url"]  # type: ignore[index]
    assert video_url.startswith("data:video/mp4;base64,")
    encoded = video_url.split(",", 1)[1]
    assert base64.b64decode(encoded) == b"fake-video"


class FakeArkTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.requests: list[ArkRequest] = []

    async def post(self, request: ArkRequest) -> dict[str, object]:
        self.requests.append(request)
        return self.response


def ark_settings() -> ArkSettings:
    return ArkSettings(
        api_key="secret-value",
        base_url="https://ark.example/api/v3",
        content_tasks_url="https://ark.example/api/v3/contents/generations/tasks",
        seed2_lite_model_id="lite-model",
        seed2_pro_model_id="pro-model",
        video_model_id="video-model",
    )


@pytest.mark.asyncio
async def test_ark_adapter_generate_returns_choice_content() -> None:
    transport = FakeArkTransport(
        response={"choices": [{"message": {"content": "{\"answers\": []}"}}]},
    )
    adapter = ArkModelAdapter(
        settings=ark_settings(),
        model_id="lite-model",
        transport=transport,
    )

    response = await adapter.generate(prompt="hello", image_uri="tos://image")

    assert response.model_name == "lite-model"
    assert response.model_provider == "ark"
    assert response.model_id == "lite-model"
    assert response.trial == 0
    assert response.raw_output == "{\"answers\": []}"
    assert transport.requests[0].json_body["model"] == "lite-model"


@pytest.mark.asyncio
async def test_ark_adapter_generate_rejects_malformed_response() -> None:
    transport = FakeArkTransport(response={"choices": []})
    adapter = ArkModelAdapter(
        settings=ark_settings(),
        model_id="lite-model",
        transport=transport,
    )

    try:
        await adapter.generate(prompt="hello", image_uri="")
    except ValueError as exc:
        assert "Unable to parse Ark response content" in str(exc)
    else:
        raise AssertionError("Expected malformed Ark response to raise ValueError")


def test_urllib_ark_transport_includes_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_http_error(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise HTTPError(
            url="https://ark.example/api/v3/chat/completions",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(b'{"error":{"message":"invalid video url"}}'),
        )

    monkeypatch.setattr("debug_agent.models.ark.urllib_request.urlopen", raise_http_error)
    request = ArkRequest(
        url="https://ark.example/api/v3/chat/completions",
        headers={"Authorization": "Bearer secret-value"},
        json_body={"model": "video-model", "messages": []},
    )

    with pytest.raises(RuntimeError, match="invalid video url"):
        UrllibArkTransport()._post_sync(request)

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from typing import Protocol
from urllib import request as urllib_request
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, Field

from debug_agent.models.adapters import ModelResponse
from debug_agent.settings import ArkSettings


VIDEO_PROXY_THRESHOLD_BYTES = 8 * 1024 * 1024


class ArkRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(repr=False)
    json_body: dict[str, object]


class ArkTransport(Protocol):
    async def post(self, request: ArkRequest) -> dict[str, object]:
        """Post an Ark request and return the decoded JSON response."""


class UrllibArkTransport:
    def __init__(self, max_attempts: int = 3, retry_delay_seconds: float = 0.5) -> None:
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def post(self, request: ArkRequest) -> dict[str, object]:
        return await asyncio.to_thread(self._post_sync, request)

    def _post_sync(self, request: ArkRequest) -> dict[str, object]:
        payload = json.dumps(request.json_body).encode("utf-8")
        http_request = urllib_request.Request(
            request.url,
            data=payload,
            headers={**request.headers, "Content-Type": "application/json"},
            method="POST",
        )
        decoded: object = {}
        for attempt in range(1, self._max_attempts + 1):
            try:
                with urllib_request.urlopen(http_request, timeout=120) as response:
                    decoded = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Ark HTTP {exc.code} {exc.reason}: {error_body}") from exc
            except URLError:
                if attempt >= self._max_attempts:
                    raise
                time.sleep(self._retry_delay_seconds)
        if not isinstance(decoded, dict):
            raise ValueError("Ark response must be a JSON object")
        return decoded


class ArkModelAdapter:
    def __init__(
        self,
        settings: ArkSettings,
        model_id: str,
        mode: str = "",
        disable_thinking: bool = False,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        transport: ArkTransport | None = None,
    ) -> None:
        self._settings = settings
        self._model_id = model_id
        self._mode = mode
        self._disable_thinking = disable_thinking
        self._temperature = temperature
        self._top_p = top_p
        self._max_tokens = max_tokens
        self._transport = transport or UrllibArkTransport()
        self._cursor = 0

    def build_request(self, prompt: str, image_uri: str) -> ArkRequest:
        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        if image_uri:
            content.append(_media_content(image_uri))
        json_body: dict[str, object] = {
            "model": self._model_id,
            "messages": [{"role": "user", "content": content}],
        }
        if self._mode:
            json_body["mode"] = self._mode
        if self._disable_thinking:
            json_body["thinking"] = {"type": "disabled"}
        if self._temperature is not None:
            json_body["temperature"] = self._temperature
        if self._top_p is not None:
            json_body["top_p"] = self._top_p
        if self._max_tokens is not None:
            json_body["max_tokens"] = self._max_tokens
        return ArkRequest(
            url=f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key.get_secret_value()}"},
            json_body=json_body,
        )

    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        request = self.build_request(prompt=prompt, image_uri=image_uri)
        response_json = await self._transport.post(request)
        trial = self._cursor
        self._cursor += 1
        return ModelResponse(
            model_name=self._model_id,
            model_provider="ark",
            model_id=self._model_id,
            trial=trial,
            raw_output=_extract_response_content(response_json),
            usage=_extract_usage(response_json),
        )


def _extract_response_content(response_json: dict[str, object]) -> str:
    try:
        choices = response_json["choices"]
        if not isinstance(choices, list) or not choices:
            raise KeyError("choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise KeyError("choices[0]")
        message = first_choice["message"]
        if not isinstance(message, dict):
            raise KeyError("message")
        content = message["content"]
        if not isinstance(content, str):
            raise KeyError("content")
        return content
    except (KeyError, IndexError) as exc:
        raise ValueError("Unable to parse Ark response content") from exc


def _extract_usage(response_json: dict[str, object]) -> dict[str, int | float]:
    usage = response_json.get("usage")
    if not isinstance(usage, dict):
        return {}
    extracted: dict[str, int | float] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int | float):
            extracted[key] = value
    return extracted


def _media_content(uri: str) -> dict[str, object]:
    if _is_video_uri(uri):
        return {"type": "video_url", "video_url": {"url": _ark_video_url(uri), "fps": 1}}
    return {"type": "image_url", "image_url": {"url": uri}}


def _is_video_uri(uri: str) -> bool:
    normalized = uri.split("?", 1)[0].lower()
    return normalized.endswith((".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"))


def _ark_video_url(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https", "data"}:
        return uri
    local_path = _resolve_local_media_path(uri)
    if local_path is None:
        raise ValueError(f"Unresolved video media URI: {uri}")
    local_path = _video_proxy_or_original(local_path)
    encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
    return f"{_video_data_uri_prefix(local_path)}{encoded}"


def _video_data_uri_prefix(local_path: Path) -> str:
    suffix = local_path.suffix.lower()
    if suffix == ".avi":
        return "data:video/avi;base64,"
    if suffix == ".mov":
        return "data:video/mov;base64,"
    return "data:video/mp4;base64,"


def _video_proxy_or_original(local_path: Path) -> Path:
    if local_path.stat().st_size <= VIDEO_PROXY_THRESHOLD_BYTES:
        return local_path
    proxy_path = _video_debug_proxy_path(local_path)
    if proxy_path.exists() and proxy_path.stat().st_size > 0:
        return proxy_path
    generated = _generate_video_debug_proxy(local_path, proxy_path)
    return generated if generated is not None else local_path


def _video_debug_proxy_path(local_path: Path) -> Path:
    project_root = Path(__file__).resolve().parents[4]
    proxy_dir = project_root / ".tmp"
    return proxy_dir / f"{local_path.stem}-debug-proxy.mp4"


def _generate_video_debug_proxy(local_path: Path, proxy_path: Path) -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    proxy_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = proxy_path.with_suffix(".tmp.mp4")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(local_path),
        "-vf",
        "scale='min(480,iw)':-2,fps=1",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "32",
        "-movflags",
        "+faststart",
        str(temp_path),
    ]
    try:
        subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
        )
        temp_path.replace(proxy_path)
    except (OSError, subprocess.CalledProcessError):
        temp_path.unlink(missing_ok=True)
        return None
    return proxy_path if proxy_path.exists() and proxy_path.stat().st_size > 0 else None


def _resolve_local_media_path(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        local_path = Path(unquote(parsed.path))
        if (
            os.name == "nt"
            and len(local_path.as_posix()) > 3
            and local_path.as_posix()[0] == "/"
            and local_path.as_posix()[2] == ":"
        ):
            local_path = Path(local_path.as_posix()[1:])
        if parsed.netloc:
            local_path = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
        return local_path if local_path.exists() else None
    return None

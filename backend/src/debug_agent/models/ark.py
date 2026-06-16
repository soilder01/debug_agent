import asyncio
import base64
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError
from typing import Protocol
from urllib import request as urllib_request
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, Field

from debug_agent.models.adapters import ModelResponse
from debug_agent.settings import ArkSettings


class ArkRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(repr=False)
    json_body: dict[str, object]


class ArkTransport(Protocol):
    async def post(self, request: ArkRequest) -> dict[str, object]:
        """Post an Ark request and return the decoded JSON response."""


class UrllibArkTransport:
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
        try:
            with urllib_request.urlopen(http_request, timeout=120) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ark HTTP {exc.code} {exc.reason}: {error_body}") from exc
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
        transport: ArkTransport | None = None,
    ) -> None:
        self._settings = settings
        self._model_id = model_id
        self._mode = mode
        self._disable_thinking = disable_thinking
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


def _media_content(uri: str) -> dict[str, object]:
    if _is_video_uri(uri):
        return {"type": "video_url", "video_url": {"url": _ark_media_url(uri)}}
    return {"type": "image_url", "image_url": {"url": uri}}


def _is_video_uri(uri: str) -> bool:
    normalized = uri.split("?", 1)[0].lower()
    return normalized.endswith((".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"))


def _ark_media_url(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return uri
    local_path = Path(unquote(parsed.path))
    if os.name == "nt" and len(local_path.as_posix()) > 3 and local_path.as_posix()[0] == "/" and local_path.as_posix()[2] == ":":
        local_path = Path(local_path.as_posix()[1:])
    if parsed.netloc:
        local_path = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
    if not local_path.exists():
        return uri
    mime_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"

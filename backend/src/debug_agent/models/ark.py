from pydantic import BaseModel, Field

from debug_agent.models.adapters import ModelResponse
from debug_agent.settings import ArkSettings


class ArkRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(repr=False)
    json_body: dict[str, object]


class ArkModelAdapter:
    def __init__(self, settings: ArkSettings, model_id: str) -> None:
        self._settings = settings
        self._model_id = model_id

    def build_request(self, prompt: str, image_uri: str) -> ArkRequest:
        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        if image_uri:
            content.append({"type": "image_url", "image_url": {"url": image_uri}})
        return ArkRequest(
            url=f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key.get_secret_value()}"},
            json_body={
                "model": self._model_id,
                "messages": [{"role": "user", "content": content}],
            },
        )

    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        del prompt, image_uri
        raise NotImplementedError("Live Ark generation is not enabled yet")

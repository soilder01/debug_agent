from typing import Protocol

from pydantic import BaseModel


class ModelResponse(BaseModel):
    model_name: str
    model_provider: str = ""
    model_id: str = ""
    trial: int
    raw_output: str
    usage: dict[str, int | float] = {}


class ModelAdapter(Protocol):
    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        """Generate a model response for one prompt/image condition."""

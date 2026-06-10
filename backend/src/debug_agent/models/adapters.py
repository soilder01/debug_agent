from typing import Protocol

from pydantic import BaseModel


class ModelResponse(BaseModel):
    model_name: str
    trial: int
    raw_output: str


class ModelAdapter(Protocol):
    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        """Generate a model response for one prompt/image condition."""

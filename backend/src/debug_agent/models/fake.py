from debug_agent.models.adapters import ModelResponse


class FakeModelAdapter:
    def __init__(self, outputs: list[str], model_name: str = "fake") -> None:
        self._outputs = outputs
        self._model_name = model_name
        self._cursor = 0

    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        del prompt, image_uri
        if not self._outputs:
            raise RuntimeError("FakeModelAdapter requires at least one output")
        trial = self._cursor
        output = self._outputs[min(self._cursor, len(self._outputs) - 1)]
        self._cursor += 1
        return ModelResponse(model_name=self._model_name, trial=trial, raw_output=output)

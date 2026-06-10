import pytest

from debug_agent.models.fake import FakeModelAdapter


@pytest.mark.asyncio
async def test_fake_model_adapter_returns_configured_outputs() -> None:
    adapter = FakeModelAdapter(outputs=["first", "second"])

    first = await adapter.generate(prompt="prompt", image_uri="")
    second = await adapter.generate(prompt="prompt", image_uri="")

    assert first.raw_output == "first"
    assert first.model_name == "fake"
    assert second.raw_output == "second"
    assert second.trial == 1

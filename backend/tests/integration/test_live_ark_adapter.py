import os

import pytest

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.models.factory import build_model_adapter
from debug_agent.settings import ModelRuntimeSettings


def _live_model_enabled() -> bool:
    return os.environ.get("DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS") == "1"


@pytest.mark.asyncio
async def test_live_ark_adapter_returns_model_output() -> None:
    if not _live_model_enabled():
        pytest.skip("Set DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS=1 to run live Ark integration tests")
    provider = os.environ.get("DEBUG_AGENT_MODEL_PROVIDER", "")
    if provider not in {"ark-seed2-lite", "ark-seed2-pro"}:
        pytest.skip("Set DEBUG_AGENT_MODEL_PROVIDER to ark-seed2-lite or ark-seed2-pro")
    if not os.environ.get("ARK_API_KEY"):
        pytest.skip("ARK_API_KEY is required for live Ark integration tests")

    case = load_fixture_case("handwrite233")
    adapter = build_model_adapter(case, settings=ModelRuntimeSettings(provider=provider))

    response = await adapter.generate(prompt=case.prompt, image_uri=case.image_uri)

    assert response.model_name
    assert response.raw_output.strip()

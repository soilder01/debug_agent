import pytest

from debug_agent.api import routes


@pytest.fixture(autouse=True)
def _use_deterministic_schema_mapping_agent(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "_case_intake_schema_mapping_agent",
        lambda: routes.SpreadsheetSchemaMappingAgent(),
    )

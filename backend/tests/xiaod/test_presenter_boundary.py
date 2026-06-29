from pathlib import Path


def test_xiaod_presenter_stays_out_of_backend_business_logic() -> None:
    source = _xiaod_source("presenter.py")
    forbidden_imports = (
        "debug_agent.api.routes",
        "debug_agent.spreadsheets",
        "debug_agent.imports",
        "debug_agent.jobs.service",
        "DebugCase",
        "SpreadsheetSchemaMappingAgent",
    )
    for forbidden in forbidden_imports:
        assert forbidden not in source


def test_xiaod_handlers_stay_out_of_backend_business_logic() -> None:
    source = _xiaod_source("handlers.py")
    forbidden_imports = (
        "debug_agent.api.routes",
        "debug_agent.spreadsheets",
        "debug_agent.imports",
        "DebugCase",
        "SpreadsheetSchemaMappingAgent",
    )
    for forbidden in forbidden_imports:
        assert forbidden not in source


def _xiaod_source(filename: str) -> str:
    return (
        Path(__file__).resolve().parents[2] / "src" / "debug_agent" / "xiaod" / filename
    ).read_text(encoding="utf-8")

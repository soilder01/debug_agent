import json
from pathlib import Path

from debug_agent.cases.models import DebugCase


def load_fixture_case(case_id: str) -> DebugCase:
    fixture_path = Path(__file__).parents[3] / "tests" / "fixtures" / f"{case_id}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture case not found: {case_id}")
    return DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

import json

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_repository_persists_imported_debug_case() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-1"})

    repository.save_case(case)

    loaded = repository.get_case("imported-1")
    assert loaded == case
    assert isinstance(loaded, DebugCase)
    assert json.loads(case.model_dump_json())["case_id"] == "imported-1"


def test_repository_lists_imported_cases_ordered_by_case_id() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    first_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-b"})
    second_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-a"})

    repository.save_case(first_case)
    repository.save_case(second_case)

    listed_cases = repository.list_cases()

    assert [case.case_id for case in listed_cases] == ["imported-a", "imported-b"]
    assert listed_cases[0] == second_case
    assert listed_cases[1] == first_case

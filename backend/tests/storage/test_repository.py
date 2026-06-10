from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base, DebugJobRow, EvidenceRow


def test_storage_tables_can_be_created() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()

    Base.metadata.create_all(engine)

    with session_factory() as session:
        session.add(DebugJobRow(job_id="job-1", case_id="case-1", status="created"))
        session.add(
            EvidenceRow(
                evidence_id="evidence-1",
                job_id="job-1",
                case_id="case-1",
                step_name="baseline",
                trial=0,
                score=0,
                reasons_json="[\"box 1 mismatch\"]",
                raw_output="{\"answers\":[]}",
            )
        )
        session.commit()

    with session_factory() as session:
        assert session.get(DebugJobRow, "job-1").status == "created"
        assert session.get(EvidenceRow, "evidence-1").step_name == "baseline"

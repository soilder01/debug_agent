from debug_agent.artifacts.store import InMemoryArtifactStore
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult


def test_store_saves_and_retrieves_evidence() -> None:
    store = InMemoryArtifactStore()
    evidence = ExperimentEvidence(
        evidence_id="case-1:baseline:0",
        step_name="baseline",
        trial=0,
        raw_output='{"answers":[]}',
        judge=JudgeResult(score=0, reasons=["box 1 missing_box"]),
    )

    store.save_case_evidence("case-1", [evidence])

    assert store.get_evidence("case-1", "case-1:baseline:0") == evidence
    assert store.list_evidence_ids("case-1") == ["case-1:baseline:0"]

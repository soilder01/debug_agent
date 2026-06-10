from debug_agent.experiments.runner import ExperimentEvidence


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._evidence_by_case: dict[str, dict[str, ExperimentEvidence]] = {}

    def save_case_evidence(self, case_id: str, evidence: list[ExperimentEvidence]) -> None:
        case_bucket = self._evidence_by_case.setdefault(case_id, {})
        for item in evidence:
            case_bucket[item.evidence_id] = item

    def get_evidence(self, case_id: str, evidence_id: str) -> ExperimentEvidence | None:
        return self._evidence_by_case.get(case_id, {}).get(evidence_id)

    def list_evidence_ids(self, case_id: str) -> list[str]:
        return sorted(self._evidence_by_case.get(case_id, {}))


artifact_store = InMemoryArtifactStore()

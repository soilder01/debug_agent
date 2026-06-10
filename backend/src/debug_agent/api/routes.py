from fastapi import APIRouter, HTTPException

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, run_experiments
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.generator import DebugReport, generate_initial_report

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}


@router.post("/cases/{case_id}/debug")
async def debug_case(case_id: str) -> DebugReport:
    try:
        case = load_fixture_case(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    plan = plan_experiments(case)
    adapter = FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])
    run_result = await run_experiments(case=case, plan=plan, adapter=adapter)
    artifact_store.save_case_evidence(case.case_id, run_result.evidence)
    return generate_initial_report(case, plan, run_result)


@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence

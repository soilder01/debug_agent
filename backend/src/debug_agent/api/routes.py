from fastapi import APIRouter, HTTPException

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
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
    return generate_initial_report(case, plan, run_result)

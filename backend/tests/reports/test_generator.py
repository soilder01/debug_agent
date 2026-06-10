import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.reports.generator import generate_initial_report


def test_generate_initial_report_for_failed_case() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)

    report = generate_initial_report(case, plan)

    assert report.case_id == "handwrite233"
    assert report.status == "needs_human_review"
    assert report.root_cause.label == "erasure_revision_failure"
    assert report.suggested_sheet_fields["debug1状态"] == "待人工确认"

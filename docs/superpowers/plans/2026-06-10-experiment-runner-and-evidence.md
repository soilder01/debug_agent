# Experiment Runner And Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn planned experiments into deterministic replay executions with judge results and evidence records.

**Architecture:** The experiment runner consumes `DebugCase`, `ExperimentPlan`, and a `ModelAdapter`, executes each planned step for its configured trial count, parses model outputs into `AnswerSet`, judges them, and returns evidence records. Reports and API responses then expose evidence summaries without requiring live model calls.

**Tech Stack:** Python 3.11, Pydantic v2, pytest-asyncio, FastAPI, existing fake model adapter and deterministic judge runner.

---

## Files

```text
backend/src/debug_agent/experiments/runner.py
backend/src/debug_agent/reports/generator.py
backend/src/debug_agent/api/routes.py
backend/tests/experiments/test_runner.py
backend/tests/reports/test_generator.py
backend/tests/api/test_case_debug.py
frontend/src/api/client.ts
frontend/src/experiments/ExperimentTimeline.tsx
frontend/src/app/App.test.tsx
```

## Task 1: Deterministic Experiment Runner

**Files:**
- Create: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [ ] **Step 1: Write runner test**

```python
import json
from pathlib import Path

import pytest

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.fake import FakeModelAdapter


@pytest.mark.asyncio
async def test_run_experiments_collects_judged_evidence() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    adapter = FakeModelAdapter(outputs=[case.predictions[0].raw_output])

    result = await run_experiments(case=case, plan=plan, adapter=adapter)

    assert result.case_id == "handwrite233"
    assert result.total_trials == 6
    assert result.success_count == 0
    assert result.evidence[0].step_name == "baseline_replay"
    assert result.evidence[0].judge.score == 0
    assert "student_answer_mismatch" in result.evidence[0].judge.reasons[0]
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/experiments/test_runner.py -q`
Expected: fails because `debug_agent.experiments.runner` does not exist.

- [ ] **Step 3: Implement runner**

```python
from pydantic import BaseModel

from debug_agent.cases.comparator import parse_prediction_answer
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.judging.runner import JudgeResult, judge_answer
from debug_agent.models.adapters import ModelAdapter


class ExperimentEvidence(BaseModel):
    evidence_id: str
    step_name: str
    trial: int
    raw_output: str
    judge: JudgeResult


class ExperimentRunResult(BaseModel):
    case_id: str
    total_trials: int
    success_count: int
    evidence: list[ExperimentEvidence]


async def run_experiments(
    case: DebugCase,
    plan: ExperimentPlan,
    adapter: ModelAdapter,
) -> ExperimentRunResult:
    evidence: list[ExperimentEvidence] = []
    success_count = 0
    for step in plan.steps:
        for trial_index in range(step.trials):
            response = await adapter.generate(prompt=case.prompt, image_uri=case.image_uri)
            predicted = parse_prediction_answer(response.raw_output)
            judge = judge_answer(case.golden_answer, predicted)
            success_count += judge.score
            evidence.append(
                ExperimentEvidence(
                    evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                    step_name=step.name,
                    trial=trial_index,
                    raw_output=response.raw_output,
                    judge=judge,
                )
            )
    return ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=success_count,
        evidence=evidence,
    )
```

- [ ] **Step 4: Verify runner**

Run: `cd backend && python -m pytest tests/experiments/test_runner.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/experiments/runner.py backend/tests/experiments/test_runner.py
git commit -m "feat: run deterministic replay experiments"
```

## Task 2: Evidence-Aware Report

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/tests/reports/test_generator.py`

- [ ] **Step 1: Add report evidence test**

Append:

```python
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.judging.runner import JudgeResult


def test_generate_report_includes_experiment_summary() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e1",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 1 student_answer_mismatch"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.total_trials == 1
    assert report.experiment_summary.success_count == 0
    assert report.experiment_summary.evidence_ids == ["e1"]
```

- [ ] **Step 2: Run failing report test**

Run: `cd backend && python -m pytest tests/reports/test_generator.py -q`
Expected: fails because `generate_initial_report` does not accept run result.

- [ ] **Step 3: Update report models**

Add to `generator.py`:

```python
class ExperimentSummary(BaseModel):
    total_trials: int
    success_count: int
    evidence_ids: list[str]
```

Modify `DebugReport`:

```python
experiment_summary: ExperimentSummary | None = None
```

Modify `generate_initial_report` signature:

```python
def generate_initial_report(
    case: DebugCase,
    plan: ExperimentPlan,
    run_result: ExperimentRunResult | None = None,
) -> DebugReport:
```

Set `experiment_summary` from run result when present.

- [ ] **Step 4: Verify reports**

Run: `cd backend && python -m pytest tests/reports/test_generator.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/reports/generator.py backend/tests/reports/test_generator.py
git commit -m "feat: include experiment evidence in reports"
```

## Task 3: API Runs Fake Experiments

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/tests/api/test_case_debug.py`

- [ ] **Step 1: Update API test**

Add assertions:

```python
assert body["experiment_summary"]["total_trials"] == 6
assert body["experiment_summary"]["success_count"] == 0
```

- [ ] **Step 2: Run failing API test**

Run: `cd backend && python -m pytest tests/api/test_case_debug.py -q`
Expected: fails because API does not run experiments yet.

- [ ] **Step 3: Update route to run fake experiments**

Use:

```python
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.fake import FakeModelAdapter
```

Change endpoint to `async def`, create fake adapter from existing prediction outputs, run experiments, pass result into report.

- [ ] **Step 4: Verify API**

Run: `cd backend && python -m pytest tests/api/test_case_debug.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/api/routes.py backend/tests/api/test_case_debug.py
git commit -m "feat: run replay experiments in debug API"
```

## Task 4: Frontend Shows Evidence Summary

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/experiments/ExperimentTimeline.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Extend frontend type and test fixture**

Add `experiment_summary` to `DebugReport` type and test mock payload.

- [ ] **Step 2: Render summary**

Update `ExperimentTimeline` props to accept optional summary and render `成功次数：x / y`.

- [ ] **Step 3: Pass summary from App**

Update `App.tsx` to pass `report.experiment_summary`.

- [ ] **Step 4: Verify frontend**

Run: `cd frontend && npx --yes pnpm@9.15.4 test -- --run && npx --yes pnpm@9.15.4 lint && npx --yes pnpm@9.15.4 typecheck`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add frontend/src
git commit -m "feat: show experiment evidence summary in UI"
```

## Task 5: Full Verification

- [ ] **Step 1: Run full verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`
Expected: all checks pass.

- [ ] **Step 2: Check working tree**

Run: `git status --short --branch`
Expected: clean working tree.

---

## Self-Review

Spec coverage:
- Planned experiments now execute deterministically.
- Evidence records include raw output and judge result.
- Reports and API expose evidence summaries.
- Frontend displays experiment result summary.

Placeholder scan:
- No placeholder or open-ended implementation steps are present.

Type consistency:
- `ExperimentRunResult`, `ExperimentEvidence`, `ExperimentSummary`, and `DebugReport` are used consistently.

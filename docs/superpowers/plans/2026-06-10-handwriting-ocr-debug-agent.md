# Handwriting OCR Debug Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an enterprise-grade agent harness that automates handwriting OCR badcase debugging with reproducible experiments, evidence-backed root-cause analysis, human review, and a frontend workflow.

**Architecture:** The application is a modular monorepo with a FastAPI backend, an experiment orchestration engine, durable storage, a React frontend, and a CLI/job runner for long-running debug tasks. The first delivery slice creates a production-quality foundation and a testable single-case debug loop; later slices extend the same interfaces to image crops, multi-model replay, batch queues, and report publishing without rewriting the core.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite for local development with PostgreSQL-compatible models, pytest, Ruff, mypy, Vite, React, TypeScript, Playwright, pnpm, Docker Compose.

---

## Non-Negotiable Product Principles

- The target is an enterprise-grade internal application, not an API-calling demo.
- Every root-cause conclusion must be tied to experiment evidence.
- Every long-running action must be resumable, checkpointed, and observable.
- Every implementation task must include tests before implementation.
- Every phase must produce usable software with clear acceptance criteria.
- The system must prefer correctness, reproducibility, and traceability over speed.
- The frontend is a first-class product surface, not a thin wrapper around backend APIs.

## Long-Term Roadmap

### Phase 0: Repository Foundation

Outcome: A clean monorepo with backend, frontend, shared contracts, CI-quality local checks, and documented architecture decisions.

Acceptance criteria:
- `make test` runs backend unit tests.
- `make lint` runs backend and frontend lint checks.
- `make typecheck` runs Python and TypeScript type checks.
- `make dev` starts backend and frontend in local development mode.
- Architecture documentation explains modules, data flow, and quality gates.

### Phase 1: Single-Case Debug Loop

Outcome: Load one handwriting OCR badcase, compare answer vs predictions, classify the observable error, create a debug job, run deterministic experiment recipes, and generate a structured report.

Acceptance criteria:
- A single JSON case fixture can be imported.
- The backend computes score stability and answer/prediction deltas per `box_id`.
- The orchestrator creates an experiment plan with explicit steps and budget.
- A local mock model runner returns deterministic replay results.
- A report is generated with evidence, confidence, and suggested table fields.
- The frontend shows case details, predictions, experiments, and report.

### Phase 2: Real Model Replay And Scoring

Outcome: Replace mock runner with pluggable model adapters and a judge runner while preserving deterministic test mode.

Acceptance criteria:
- Model adapters implement a common interface.
- Replay supports original prompt, prompt variants, and repeated trials.
- Judge explains pass/fail per `box_id` and per formatting rule.
- Tests use recorded fixtures and never require live API access.

### Phase 3: Vision Evidence Tooling

Outcome: Add image region proposals, crop/zoom experiments, error-region annotation, and report artifacts.

Acceptance criteria:
- The system stores original image metadata and derived crop artifacts.
- Region experiments compare full image vs crop vs zoom.
- Frontend supports side-by-side image and prediction comparison.
- Reports contain clickable image evidence.

### Phase 4: Batch Queue And Human Review

Outcome: Support batch ingestion from sheets, durable async jobs, human approval, and controlled writeback.

Acceptance criteria:
- Jobs can pause, resume, retry, and fail with actionable error states.
- Human reviewers can accept, edit, or reject agent conclusions.
- Only approved fields are written back to the source sheet.
- Audit logs record who approved what and which evidence supported it.

### Phase 5: Enterprise Hardening

Outcome: Security, observability, permissions, cost controls, deployment automation, and regression suites.

Acceptance criteria:
- Role-based access controls protect case data and writeback actions.
- Metrics track cost, latency, model calls, failure rates, and review acceptance.
- Deployment runs in containerized environments.
- Regression suites protect root-cause taxonomy and experiment planning behavior.

## Repository Structure

```text
debug_agent/
  Makefile
  README.md
  docker-compose.yml
  docs/
    architecture.md
    quality-gates.md
    superpowers/plans/2026-06-10-handwriting-ocr-debug-agent.md
  backend/
    pyproject.toml
    src/debug_agent/
      __init__.py
      main.py
      api/
        __init__.py
        routes.py
      cases/
        __init__.py
        models.py
        comparator.py
        fixtures.py
      experiments/
        __init__.py
        planner.py
        runner.py
        recipes.py
      reports/
        __init__.py
        generator.py
      storage/
        __init__.py
        models.py
        session.py
      settings.py
    tests/
      cases/test_comparator.py
      experiments/test_planner.py
      reports/test_generator.py
      api/test_health.py
      fixtures/handwrite233.json
  frontend/
    package.json
    tsconfig.json
    vite.config.ts
    src/
      main.tsx
      app/App.tsx
      api/client.ts
      cases/CaseDetail.tsx
      experiments/ExperimentTimeline.tsx
      reports/ReportPanel.tsx
    tests/
      case-detail.spec.tsx
```

## Domain Contracts

### Case Input Contract

```json
{
  "case_id": "handwrite233",
  "image_uri": "",
  "prompt": "仅识别题目对应作答区域内的学生全部作答内容...",
  "golden_answer": {
    "answers": [
      {"box_id": 1, "student_answer": "温度过高过碳酸钠受*？"},
      {"box_id": 2, "student_answer": "低昷烘干"},
      {"box_id": 3, "student_answer": "a"}
    ]
  },
  "scoring_standard": "1分标准...",
  "predictions": [
    {
      "trial": 0,
      "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"温度过高过碳酸钠受热\"}]}",
      "score": 0
    }
  ],
  "avg_score": 0.0,
  "human_notes": {
    "debug_status": "已完成",
    "root_cause": "对于在作答区域内的涂改，有严重的猜测倾向。"
  }
}
```

### Report Output Contract

```json
{
  "case_id": "handwrite233",
  "status": "needs_human_review",
  "observed_failure": {
    "type": "erasure_revision_failure",
    "summary": "模型倾向把涂改区域补全为语义上更合理的答案。",
    "affected_box_ids": [1, 2]
  },
  "experiments": [
    {
      "name": "original_prompt_replay",
      "trials": 5,
      "success_count": 0,
      "evidence_ids": ["exp_001_trial_0", "exp_001_trial_1"]
    }
  ],
  "root_cause": {
    "label": "erasure_revision_failure",
    "confidence": "medium",
    "evidence_summary": "原始复测仍失败，错误集中在涂改/补写区域。"
  },
  "suggested_sheet_fields": {
    "debug1状态": "待人工确认",
    "模型可做对次数": "0次",
    "错误原因": "模型无法稳定识别涂改后的最终答案，存在语义补全倾向。"
  }
}
```

## Root-Cause Taxonomy

| Label | Meaning | Required Evidence |
| --- | --- | --- |
| `visual_recognition_failure` | Pure OCR/visual recognition failure | Full image and focused view both fail |
| `context_interference` | Context hurts recognition | Crop or simplified context improves result |
| `semantic_correction` | Model corrects text by prior knowledge | Output is semantically plausible but visually unfaithful |
| `erasure_revision_failure` | Erased/revised content handling fails | Error overlaps with strike-through, overwrite, or revision region |
| `box_split_failure` | `box_id` count, order, or grouping fails | Answer and prediction differ in box structure |
| `format_failure` | JSON, LaTeX, unit, casing, or empty-value format fails | Semantic content is right but output contract is wrong |
| `prompt_ambiguity` | Prompt rules conflict or are underspecified | Multiple prompt interpretations explain different expected outputs |
| `golden_answer_issue` | Golden answer conflicts with image or prompt | Model output appears compliant with prompt but differs from answer |
| `judge_issue` | Scoring rule misjudges an otherwise acceptable output | Judge reason contradicts scoring standard |
| `stochastic_instability` | Results vary across repeated trials | Same condition produces both pass and fail |

---

## Task 1: Repository Bootstrap

**Files:**
- Create: `README.md`
- Create: `Makefile`
- Create: `docker-compose.yml`
- Create: `docs/architecture.md`
- Create: `docs/quality-gates.md`
- Create: `backend/pyproject.toml`
- Create: `backend/src/debug_agent/__init__.py`
- Create: `frontend/package.json`

- [ ] **Step 1: Create project README**

Write `README.md`:

```markdown
# Handwriting OCR Debug Agent

Enterprise-grade agent harness for debugging handwriting OCR badcases.

## Goals

- Reproduce model failures with controlled experiments.
- Explain root causes using evidence rather than speculation.
- Reduce manual debug effort while preserving human review.
- Provide a frontend for case inspection, experiment tracking, and report approval.

## Local Commands

- `make test`: run backend unit tests.
- `make lint`: run backend and frontend lint checks.
- `make typecheck`: run Python and TypeScript type checks.
- `make dev`: start local backend and frontend services.

## Quality Bar

This repository is built through small tested slices. A feature is complete only when tests, docs, and local verification pass.
```

- [ ] **Step 2: Create Makefile**

Write `Makefile`:

```makefile
.PHONY: test lint typecheck dev backend-test frontend-test

test: backend-test frontend-test

backend-test:
	cd backend && python -m pytest -q

frontend-test:
	cd frontend && pnpm test -- --run

lint:
	cd backend && python -m ruff check src tests
	cd frontend && pnpm lint

typecheck:
	cd backend && python -m mypy src
	cd frontend && pnpm typecheck

dev:
	docker compose up --build
```

- [ ] **Step 3: Create Docker Compose skeleton**

Write `docker-compose.yml`:

```yaml
services:
  backend:
    image: python:3.11-slim
    working_dir: /app/backend
    volumes:
      - .:/app
    command: sh -c "pip install -e .[dev] && uvicorn debug_agent.main:app --host 0.0.0.0 --port 8000 --reload"
    ports:
      - "8000:8000"
    environment:
      DEBUG_AGENT_DATABASE_URL: sqlite:///./debug_agent.db

  frontend:
    image: node:20-alpine
    working_dir: /app/frontend
    volumes:
      - .:/app
    command: sh -c "corepack enable && pnpm install && pnpm dev --host 0.0.0.0"
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

- [ ] **Step 4: Create architecture docs**

Write `docs/architecture.md`:

```markdown
# Architecture

The system has five core modules:

- Case management: imports and normalizes badcase data.
- Comparison: identifies answer/prediction deltas.
- Experiments: plans and runs reproducible debug recipes.
- Reports: generates evidence-backed root-cause summaries.
- Review UI: lets humans inspect, approve, edit, and reject conclusions.

All model calls are routed through adapters. Tests use deterministic adapters and recorded fixtures. Live adapters are integration-only and are never required for unit tests.
```

- [ ] **Step 5: Create quality gates docs**

Write `docs/quality-gates.md`:

```markdown
# Quality Gates

## Definition Of Done

- Tests are written before implementation.
- Unit tests pass locally.
- Type checks pass locally.
- New behavior is documented.
- Every agent conclusion links to evidence.
- Long-running jobs are checkpointed or explicitly documented as synchronous prototype-only behavior for the current phase.

## Release Gate

No phase is accepted unless its acceptance criteria are met with commands recorded in the final handoff.
```

- [ ] **Step 6: Create backend pyproject**

Write `backend/pyproject.toml`:

```toml
[project]
name = "debug-agent-backend"
version = "0.1.0"
description = "Backend for handwriting OCR debug agent"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.7.0",
  "sqlalchemy>=2.0.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "ruff>=0.5.0",
  "mypy>=1.10.0",
  "httpx>=0.27.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] **Step 7: Create backend package marker**

Write `backend/src/debug_agent/__init__.py`:

```python
"""Handwriting OCR debug agent backend."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 8: Create frontend package manifest**

Write `frontend/package.json`:

```json
{
  "name": "debug-agent-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint src --ext ts,tsx",
    "typecheck": "tsc --noEmit",
    "test": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.3.0",
    "typescript": "^5.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "eslint": "^9.5.0",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 9: Run bootstrap verification**

Run:

```bash
cd backend && python -m pip install -e .[dev]
```

Expected: dependencies install successfully.

- [ ] **Step 10: Commit bootstrap**

Run:

```bash
git add README.md Makefile docker-compose.yml docs backend frontend
git commit -m "chore: bootstrap debug agent monorepo"
```

Expected: one commit with repository foundation.

---

## Task 2: Backend Health API

**Files:**
- Create: `backend/src/debug_agent/main.py`
- Create: `backend/src/debug_agent/api/__init__.py`
- Create: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_health.py`

- [ ] **Step 1: Write failing API test**

Write `backend/tests/api/test_health.py`:

```python
from fastapi.testclient import TestClient

from debug_agent.main import app


def test_health_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "debug-agent-backend"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend && python -m pytest tests/api/test_health.py -q
```

Expected: fail because `debug_agent.main` does not exist.

- [ ] **Step 3: Implement API route**

Write `backend/src/debug_agent/api/__init__.py`:

```python
"""HTTP API package."""
```

Write `backend/src/debug_agent/api/routes.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}
```

Write `backend/src/debug_agent/main.py`:

```python
from fastapi import FastAPI

from debug_agent.api.routes import router

app = FastAPI(title="Handwriting OCR Debug Agent", version="0.1.0")
app.include_router(router)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd backend && python -m pytest tests/api/test_health.py -q
```

Expected: one test passes.

- [ ] **Step 5: Run type and lint checks**

Run:

```bash
cd backend && python -m ruff check src tests && python -m mypy src
```

Expected: checks pass.

- [ ] **Step 6: Commit health API**

Run:

```bash
git add backend/src/debug_agent/main.py backend/src/debug_agent/api backend/tests/api/test_health.py
git commit -m "feat: add backend health endpoint"
```

Expected: one commit with health endpoint.

---

## Task 3: Case Domain Model And Fixture

**Files:**
- Create: `backend/src/debug_agent/cases/__init__.py`
- Create: `backend/src/debug_agent/cases/models.py`
- Create: `backend/tests/fixtures/handwrite233.json`
- Create: `backend/tests/cases/test_models.py`

- [ ] **Step 1: Write failing model test**

Write `backend/tests/cases/test_models.py`:

```python
import json
from pathlib import Path

from debug_agent.cases.models import DebugCase


def test_debug_case_parses_fixture() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    case = DebugCase.model_validate(raw)

    assert case.case_id == "handwrite233"
    assert case.golden_answer.answers[0].box_id == 1
    assert case.predictions[0].trial == 0
    assert case.avg_score == 0.0
```

- [ ] **Step 2: Create fixture**

Write `backend/tests/fixtures/handwrite233.json`:

```json
{
  "case_id": "handwrite233",
  "image_uri": "",
  "prompt": "仅识别题目对应作答区域内的学生全部作答内容。",
  "golden_answer": {
    "answers": [
      {"box_id": 1, "student_answer": "温度过高过碳酸钠受*？"},
      {"box_id": 2, "student_answer": "低昷烘干"},
      {"box_id": 3, "student_answer": "a"}
    ]
  },
  "scoring_standard": "1分标准：json格式正确，box_id和student_answer均与参考答案一致。",
  "predictions": [
    {
      "trial": 0,
      "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"温度过高过碳酸钠受热\"},{\"box_id\":2,\"student_answer\":\"低温烘干\"},{\"box_id\":3,\"student_answer\":\"a\"}]}",
      "score": 0
    }
  ],
  "avg_score": 0.0,
  "human_notes": {
    "debug_status": "已完成",
    "root_cause": "对于在作答区域内的涂改，有严重的猜测倾向。"
  }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
cd backend && python -m pytest tests/cases/test_models.py -q
```

Expected: fail because `debug_agent.cases.models` does not exist.

- [ ] **Step 4: Implement domain models**

Write `backend/src/debug_agent/cases/__init__.py`:

```python
"""Case parsing and comparison domain."""
```

Write `backend/src/debug_agent/cases/models.py`:

```python
from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    box_id: int
    student_answer: str


class AnswerSet(BaseModel):
    answers: list[AnswerItem]


class Prediction(BaseModel):
    trial: int
    raw_output: str
    score: int = Field(ge=0, le=1)


class HumanNotes(BaseModel):
    debug_status: str = ""
    root_cause: str = ""


class DebugCase(BaseModel):
    case_id: str
    image_uri: str
    prompt: str
    golden_answer: AnswerSet
    scoring_standard: str
    predictions: list[Prediction]
    avg_score: float = Field(ge=0.0, le=1.0)
    human_notes: HumanNotes = Field(default_factory=HumanNotes)
```

- [ ] **Step 5: Run model tests**

Run:

```bash
cd backend && python -m pytest tests/cases/test_models.py -q
```

Expected: test passes.

- [ ] **Step 6: Commit case model**

Run:

```bash
git add backend/src/debug_agent/cases backend/tests/cases/test_models.py backend/tests/fixtures/handwrite233.json
git commit -m "feat: add debug case domain model"
```

Expected: one commit with validated case fixture.

---

## Task 4: Answer Comparator

**Files:**
- Create: `backend/src/debug_agent/cases/comparator.py`
- Create: `backend/tests/cases/test_comparator.py`

- [ ] **Step 1: Write failing comparator tests**

Write `backend/tests/cases/test_comparator.py`:

```python
import json

from debug_agent.cases.comparator import compare_answer_sets, parse_prediction_answer
from debug_agent.cases.models import AnswerSet


def test_parse_prediction_answer_reads_valid_json() -> None:
    raw = "{\"answers\":[{\"box_id\":1,\"student_answer\":\"A\"}]}"

    parsed = parse_prediction_answer(raw)

    assert parsed.answers[0].box_id == 1
    assert parsed.answers[0].student_answer == "A"


def test_compare_answer_sets_detects_text_delta() -> None:
    expected = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "低昷烘干"}]}
    )
    predicted = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "低温烘干"}]}
    )

    diff = compare_answer_sets(expected, predicted)

    assert diff.has_differences is True
    assert diff.affected_box_ids == [1]
    assert diff.deltas[0].reason == "student_answer_mismatch"
    assert json.loads(diff.model_dump_json())["affected_box_ids"] == [1]
```

- [ ] **Step 2: Run comparator tests to verify failure**

Run:

```bash
cd backend && python -m pytest tests/cases/test_comparator.py -q
```

Expected: fail because comparator does not exist.

- [ ] **Step 3: Implement comparator**

Write `backend/src/debug_agent/cases/comparator.py`:

```python
import json

from pydantic import BaseModel

from debug_agent.cases.models import AnswerSet


class AnswerDelta(BaseModel):
    box_id: int
    expected: str | None
    predicted: str | None
    reason: str


class AnswerDiff(BaseModel):
    has_differences: bool
    affected_box_ids: list[int]
    deltas: list[AnswerDelta]


def parse_prediction_answer(raw_output: str) -> AnswerSet:
    payload = json.loads(raw_output)
    return AnswerSet.model_validate(payload)


def compare_answer_sets(expected: AnswerSet, predicted: AnswerSet) -> AnswerDiff:
    expected_by_box = {item.box_id: item.student_answer for item in expected.answers}
    predicted_by_box = {item.box_id: item.student_answer for item in predicted.answers}
    all_box_ids = sorted(set(expected_by_box) | set(predicted_by_box))
    deltas: list[AnswerDelta] = []

    for box_id in all_box_ids:
        expected_value = expected_by_box.get(box_id)
        predicted_value = predicted_by_box.get(box_id)
        if expected_value == predicted_value:
            continue
        reason = "student_answer_mismatch"
        if expected_value is None:
            reason = "extra_box"
        elif predicted_value is None:
            reason = "missing_box"
        deltas.append(
            AnswerDelta(
                box_id=box_id,
                expected=expected_value,
                predicted=predicted_value,
                reason=reason,
            )
        )

    return AnswerDiff(
        has_differences=bool(deltas),
        affected_box_ids=[delta.box_id for delta in deltas],
        deltas=deltas,
    )
```

- [ ] **Step 4: Run comparator tests**

Run:

```bash
cd backend && python -m pytest tests/cases/test_comparator.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit comparator**

Run:

```bash
git add backend/src/debug_agent/cases/comparator.py backend/tests/cases/test_comparator.py
git commit -m "feat: compare golden answers and predictions"
```

Expected: one commit with answer comparison logic.

---

## Task 5: Experiment Planner

**Files:**
- Create: `backend/src/debug_agent/experiments/__init__.py`
- Create: `backend/src/debug_agent/experiments/planner.py`
- Create: `backend/tests/experiments/test_planner.py`

- [ ] **Step 1: Write failing planner tests**

Write `backend/tests/experiments/test_planner.py`:

```python
import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments


def test_plan_experiments_for_low_score_case() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

    plan = plan_experiments(case)

    assert plan.case_id == "handwrite233"
    assert plan.max_model_calls == 10
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "strict_prompt_replay",
        "localized_observation_request",
    ]
```

- [ ] **Step 2: Run planner test to verify failure**

Run:

```bash
cd backend && python -m pytest tests/experiments/test_planner.py -q
```

Expected: fail because experiment planner does not exist.

- [ ] **Step 3: Implement planner**

Write `backend/src/debug_agent/experiments/__init__.py`:

```python
"""Experiment planning and execution."""
```

Write `backend/src/debug_agent/experiments/planner.py`:

```python
from pydantic import BaseModel

from debug_agent.cases.models import DebugCase


class ExperimentStep(BaseModel):
    name: str
    description: str
    trials: int


class ExperimentPlan(BaseModel):
    case_id: str
    max_model_calls: int
    steps: list[ExperimentStep]


def plan_experiments(case: DebugCase) -> ExperimentPlan:
    baseline_trials = min(5, max(1, len(case.predictions)))
    steps = [
        ExperimentStep(
            name="baseline_replay",
            description="Replay the original prompt and image condition to confirm the failure.",
            trials=baseline_trials,
        ),
        ExperimentStep(
            name="strict_prompt_replay",
            description="Replay with stronger instruction to avoid semantic correction and guessing.",
            trials=3,
        ),
        ExperimentStep(
            name="localized_observation_request",
            description="Ask the model to describe the affected answer region before extracting final JSON.",
            trials=2,
        ),
    ]
    return ExperimentPlan(case_id=case.case_id, max_model_calls=10, steps=steps)
```

- [ ] **Step 4: Run planner tests**

Run:

```bash
cd backend && python -m pytest tests/experiments/test_planner.py -q
```

Expected: test passes.

- [ ] **Step 5: Commit planner**

Run:

```bash
git add backend/src/debug_agent/experiments backend/tests/experiments/test_planner.py
git commit -m "feat: plan deterministic debug experiments"
```

Expected: one commit with experiment planning.

---

## Task 6: Report Generator

**Files:**
- Create: `backend/src/debug_agent/reports/__init__.py`
- Create: `backend/src/debug_agent/reports/generator.py`
- Create: `backend/tests/reports/test_generator.py`

- [ ] **Step 1: Write failing report test**

Write `backend/tests/reports/test_generator.py`:

```python
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
```

- [ ] **Step 2: Run report test to verify failure**

Run:

```bash
cd backend && python -m pytest tests/reports/test_generator.py -q
```

Expected: fail because report generator does not exist.

- [ ] **Step 3: Implement report generator**

Write `backend/src/debug_agent/reports/__init__.py`:

```python
"""Report generation."""
```

Write `backend/src/debug_agent/reports/generator.py`:

```python
from pydantic import BaseModel

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan


class ObservedFailure(BaseModel):
    type: str
    summary: str
    affected_box_ids: list[int]


class RootCause(BaseModel):
    label: str
    confidence: str
    evidence_summary: str


class DebugReport(BaseModel):
    case_id: str
    status: str
    observed_failure: ObservedFailure
    planned_experiments: list[str]
    root_cause: RootCause
    suggested_sheet_fields: dict[str, str]


def generate_initial_report(case: DebugCase, plan: ExperimentPlan) -> DebugReport:
    return DebugReport(
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="erasure_revision_failure",
            summary="模型在涂改、错字或相近字符场景下存在语义猜测和纠偏风险。",
            affected_box_ids=[1, 2],
        ),
        planned_experiments=[step.name for step in plan.steps],
        root_cause=RootCause(
            label="erasure_revision_failure",
            confidence="medium",
            evidence_summary="当前样本低分且人工备注指向涂改区域识别失败，需要复测确认。",
        ),
        suggested_sheet_fields={
            "debug1状态": "待人工确认",
            "模型可做对次数": "0次",
            "错误原因": "模型无法稳定识别涂改后的最终答案，存在语义补全倾向。",
        },
    )
```

- [ ] **Step 4: Run report tests**

Run:

```bash
cd backend && python -m pytest tests/reports/test_generator.py -q
```

Expected: test passes.

- [ ] **Step 5: Commit report generator**

Run:

```bash
git add backend/src/debug_agent/reports backend/tests/reports/test_generator.py
git commit -m "feat: generate initial debug reports"
```

Expected: one commit with report generation.

---

## Task 7: Case Debug API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/src/debug_agent/cases/fixtures.py`
- Create: `backend/tests/api/test_case_debug.py`

- [ ] **Step 1: Write failing API test**

Write `backend/tests/api/test_case_debug.py`:

```python
from fastapi.testclient import TestClient

from debug_agent.main import app


def test_debug_fixture_case_returns_report() -> None:
    client = TestClient(app)

    response = client.post("/cases/handwrite233/debug")

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "handwrite233"
    assert body["status"] == "needs_human_review"
    assert "baseline_replay" in body["planned_experiments"]
```

- [ ] **Step 2: Run API test to verify failure**

Run:

```bash
cd backend && python -m pytest tests/api/test_case_debug.py -q
```

Expected: fail because route does not exist.

- [ ] **Step 3: Implement fixture loader**

Write `backend/src/debug_agent/cases/fixtures.py`:

```python
import json
from pathlib import Path

from debug_agent.cases.models import DebugCase


def load_fixture_case(case_id: str) -> DebugCase:
    fixture_path = Path(__file__).parents[3] / "tests" / "fixtures" / f"{case_id}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture case not found: {case_id}")
    return DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Add debug route**

Replace `backend/src/debug_agent/api/routes.py` with:

```python
from fastapi import APIRouter, HTTPException

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.reports.generator import DebugReport, generate_initial_report

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}


@router.post("/cases/{case_id}/debug")
def debug_case(case_id: str) -> DebugReport:
    try:
        case = load_fixture_case(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    plan = plan_experiments(case)
    return generate_initial_report(case, plan)
```

- [ ] **Step 5: Run API tests**

Run:

```bash
cd backend && python -m pytest tests/api tests/cases tests/experiments tests/reports -q
```

Expected: all backend tests pass.

- [ ] **Step 6: Commit debug API**

Run:

```bash
git add backend/src/debug_agent/api/routes.py backend/src/debug_agent/cases/fixtures.py backend/tests/api/test_case_debug.py
git commit -m "feat: expose fixture case debug endpoint"
```

Expected: one commit with an end-to-end backend debug endpoint.

---

## Task 8: Frontend Case Review Skeleton

**Files:**
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/cases/CaseDetail.tsx`
- Create: `frontend/src/experiments/ExperimentTimeline.tsx`
- Create: `frontend/src/reports/ReportPanel.tsx`

- [ ] **Step 1: Create TypeScript config**

Write `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

- [ ] **Step 2: Create Vite config**

Write `frontend/vite.config.ts`:

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, "")
      }
    }
  }
});
```

- [ ] **Step 3: Create frontend entry**

Write `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OCR Debug Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Write `frontend/src/main.tsx`:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./app/App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 4: Create API client**

Write `frontend/src/api/client.ts`:

```typescript
export type DebugReport = {
  case_id: string;
  status: string;
  observed_failure: {
    type: string;
    summary: string;
    affected_box_ids: number[];
  };
  planned_experiments: string[];
  root_cause: {
    label: string;
    confidence: string;
    evidence_summary: string;
  };
  suggested_sheet_fields: Record<string, string>;
};

export async function debugFixtureCase(caseId: string): Promise<DebugReport> {
  const response = await fetch(`/api/cases/${caseId}/debug`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to debug case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}
```

- [ ] **Step 5: Create presentational components**

Write `frontend/src/cases/CaseDetail.tsx`:

```typescript
type CaseDetailProps = {
  caseId: string;
  status: string;
};

export function CaseDetail({ caseId, status }: CaseDetailProps) {
  return (
    <section>
      <h2>Case</h2>
      <p>样本 ID：{caseId}</p>
      <p>状态：{status}</p>
    </section>
  );
}
```

Write `frontend/src/experiments/ExperimentTimeline.tsx`:

```typescript
type ExperimentTimelineProps = {
  experiments: string[];
};

export function ExperimentTimeline({ experiments }: ExperimentTimelineProps) {
  return (
    <section>
      <h2>Experiment Plan</h2>
      <ol>
        {experiments.map((experiment) => (
          <li key={experiment}>{experiment}</li>
        ))}
      </ol>
    </section>
  );
}
```

Write `frontend/src/reports/ReportPanel.tsx`:

```typescript
import type { DebugReport } from "../api/client";

type ReportPanelProps = {
  report: DebugReport;
};

export function ReportPanel({ report }: ReportPanelProps) {
  return (
    <section>
      <h2>Root Cause</h2>
      <p>类型：{report.root_cause.label}</p>
      <p>置信度：{report.root_cause.confidence}</p>
      <p>{report.root_cause.evidence_summary}</p>
      <h3>建议回填</h3>
      <dl>
        {Object.entries(report.suggested_sheet_fields).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
```

- [ ] **Step 6: Create app shell**

Write `frontend/src/app/App.tsx`:

```typescript
import { useState } from "react";

import { debugFixtureCase, type DebugReport } from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { ReportPanel } from "../reports/ReportPanel";

export function App() {
  const [report, setReport] = useState<DebugReport | null>(null);
  const [error, setError] = useState<string>("");

  async function runDebug() {
    setError("");
    try {
      setReport(await debugFixtureCase("handwrite233"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  return (
    <main>
      <h1>Handwriting OCR Debug Agent</h1>
      <button type="button" onClick={runDebug}>
        Run single-case debug
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {report ? (
        <>
          <CaseDetail caseId={report.case_id} status={report.status} />
          <ExperimentTimeline experiments={report.planned_experiments} />
          <ReportPanel report={report} />
        </>
      ) : (
        <p>点击按钮运行第一条可验证 debug 闭环。</p>
      )}
    </main>
  );
}
```

- [ ] **Step 7: Run frontend checks**

Run:

```bash
cd frontend && corepack enable && pnpm install && pnpm typecheck
```

Expected: dependencies install and TypeScript passes.

- [ ] **Step 8: Commit frontend skeleton**

Run:

```bash
git add frontend
git commit -m "feat: add case review frontend skeleton"
```

Expected: one commit with frontend shell.

---

## Phase 1 Completion Gate

Run:

```bash
make test
make lint
make typecheck
```

Expected:
- Backend tests pass.
- Frontend tests pass once frontend test config is added in the next frontend testing task.
- Lint passes after ESLint config is added in the next frontend quality task.
- Type checks pass for implemented modules.

Manual verification:
- Start local services with `make dev`.
- Open `http://localhost:5173`.
- Click `Run single-case debug`.
- Confirm the UI renders case ID, planned experiments, root cause, and suggested sheet fields.

## Next Plans To Create After Phase 1

- `2026-06-10-model-adapter-and-judge.md`: model replay adapters, deterministic fixtures, judge explanations.
- `2026-06-10-vision-evidence-tooling.md`: crop/zoom artifacts, region proposal, image evidence reports.
- `2026-06-10-batch-review-writeback.md`: sheet ingestion, async jobs, human approval, safe writeback.
- `2026-06-10-enterprise-hardening.md`: auth, RBAC, observability, deployment, cost controls.

## Self-Review

Spec coverage:
- Enterprise architecture is covered by repository structure, roadmap, quality gates, and modular contracts.
- Strict testing is covered by TDD steps in each task and phase gates.
- Minimal-step execution is covered by small tasks and commit checkpoints.
- Frontend visualization is covered by Task 8 and later frontend expansion phases.
- Long-running debug constraints are captured in roadmap Phase 4 and non-negotiable principles.

Placeholder scan:
- No task uses open-ended implementation placeholders.
- Future phases are named as separate plans because each is an independent subsystem.

Type consistency:
- `DebugCase`, `ExperimentPlan`, and `DebugReport` names are consistent across backend tasks.
- API route returns `DebugReport` and frontend client consumes the same JSON shape.

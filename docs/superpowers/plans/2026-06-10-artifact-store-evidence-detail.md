# Artifact Store Evidence Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist replay evidence in a backend store and expose evidence detail through API and frontend drilldown.

**Architecture:** Add a small artifact store abstraction with an in-memory implementation for the current local harness. The debug API writes experiment evidence into the store, a new evidence detail API reads from it, and the frontend fetches and renders individual evidence details on demand.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, React 18, TypeScript, Vitest, Testing Library.

---

## Files

```text
backend/src/debug_agent/artifacts/__init__.py
backend/src/debug_agent/artifacts/store.py
backend/src/debug_agent/api/routes.py
backend/tests/artifacts/__init__.py
backend/tests/artifacts/test_store.py
backend/tests/api/test_evidence_detail.py
frontend/src/api/client.ts
frontend/src/experiments/ExperimentTimeline.tsx
frontend/src/evidence/EvidenceDetail.tsx
frontend/src/app/App.tsx
frontend/src/app/App.test.tsx
```

## Task 1: Artifact Store

**Files:**
- Create: `backend/src/debug_agent/artifacts/__init__.py`
- Create: `backend/src/debug_agent/artifacts/store.py`
- Create: `backend/tests/artifacts/__init__.py`
- Create: `backend/tests/artifacts/test_store.py`

- [ ] **Step 1: Write store test**

Create `backend/tests/artifacts/test_store.py`:

```python
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
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/artifacts/test_store.py -q`
Expected: fails because artifact store does not exist.

- [ ] **Step 3: Implement store**

Create `backend/src/debug_agent/artifacts/store.py`:

```python
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
```

- [ ] **Step 4: Verify and commit**

Run:
```bash
cd backend && python -m pytest tests/artifacts/test_store.py -q
cd backend && python -m ruff check src tests && python -m mypy src
git add backend/src/debug_agent/artifacts backend/tests/artifacts
git commit -m "feat: add in-memory artifact store"
```

## Task 2: Evidence Detail API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_evidence_detail.py`

- [ ] **Step 1: Write API test**

Create `backend/tests/api/test_evidence_detail.py`:

```python
from fastapi.testclient import TestClient

from debug_agent.main import app


def test_evidence_detail_returns_stored_replay_evidence() -> None:
    client = TestClient(app)
    debug_response = client.post("/cases/handwrite233/debug")
    evidence_id = debug_response.json()["experiment_summary"]["evidence_ids"][0]

    response = client.get(f"/cases/handwrite233/evidence/{evidence_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_id"] == evidence_id
    assert body["step_name"] == "baseline_replay"
    assert body["judge"]["score"] == 0
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/api/test_evidence_detail.py -q`
Expected: fails because evidence detail route does not exist.

- [ ] **Step 3: Implement route**

Update `routes.py` to import `artifact_store` and `ExperimentEvidence`, save evidence after debug runs, and add:

```python
@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence
```

- [ ] **Step 4: Verify and commit**

Run:
```bash
cd backend && python -m pytest tests/api/test_evidence_detail.py -q
cd backend && python -m pytest tests -q && python -m ruff check src tests && python -m mypy src
git add backend/src/debug_agent/api/routes.py backend/tests/api/test_evidence_detail.py
git commit -m "feat: expose evidence detail API"
```

## Task 3: Frontend Evidence Drilldown

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/experiments/ExperimentTimeline.tsx`
- Create: `frontend/src/evidence/EvidenceDetail.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Extend client**

Add `ExperimentEvidence` type and `fetchEvidenceDetail(caseId, evidenceId)` function.

- [ ] **Step 2: Add evidence detail component**

Create a component rendering selected evidence id, step, trial, score, reasons, and raw output in a `<pre>`.

- [ ] **Step 3: Render evidence buttons**

Update `ExperimentTimeline` to render each evidence id as a button and call `onSelectEvidence(evidenceId)`.

- [ ] **Step 4: Wire App state**

Add selected evidence state and fetch detail when a button is clicked.

- [ ] **Step 5: Update test**

Mock two fetch calls: debug response and evidence detail response. Assert evidence raw output and judge reason render after clicking an evidence button.

- [ ] **Step 6: Verify and commit**

Run:
```bash
cd frontend && npx --yes pnpm@9.15.4 test -- --run
cd frontend && npx --yes pnpm@9.15.4 lint && npx --yes pnpm@9.15.4 typecheck
git add frontend/src
git commit -m "feat: add evidence detail drilldown UI"
```

## Task 4: Full Verification

- [ ] **Step 1: Run full verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`
Expected: all checks pass.

- [ ] **Step 2: Check working tree**

Run: `git status --short --branch`
Expected: clean working tree.

---

## Self-Review

Spec coverage:
- Evidence is persisted in a backend store.
- Evidence details are available by API.
- Frontend supports evidence drilldown.
- All behavior is test-covered without live model calls.

Placeholder scan:
- No placeholder or open-ended implementation steps are present.

Type consistency:
- `ExperimentEvidence` is shared by runner, store, API response, and frontend type definitions.

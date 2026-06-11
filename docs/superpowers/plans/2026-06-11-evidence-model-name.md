# Evidence Model Name Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Persist the model name used for each experiment evidence item.

**Architecture:** Extend `ExperimentEvidence` with `model_name`, fill it from `ModelResponse.model_name`, persist it on `EvidenceRow`, and add a lightweight SQLite schema migration for existing `evidence` tables.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic v2, pytest, mypy.

---

## File Structure

- Modify `backend/src/debug_agent/experiments/runner.py`: include `model_name` in evidence.
- Modify `backend/src/debug_agent/storage/models.py`: add `EvidenceRow.model_name`.
- Modify `backend/src/debug_agent/storage/repository.py`: save model name.
- Modify `backend/src/debug_agent/storage/database.py`: add missing-column migration.
- Modify `backend/tests/experiments/test_runner.py`: assert evidence model name.
- Modify `backend/tests/storage/test_repository.py`: assert persisted model name and migration.
- Create `docs/superpowers/plans/2026-06-11-evidence-model-name.md`: this plan.

## Task 1: Evidence Carries Model Name

- [x] **Step 1: Write failing runner test**

Assert `result.evidence[0].model_name == "fake"` in `backend/tests/experiments/test_runner.py`.

- [x] **Step 2: Implement evidence field**

Add `model_name` to `ExperimentEvidence` and set it from `response.model_name`.

- [x] **Step 3: Run focused test**

Run:

```powershell
python -m pytest tests/experiments/test_runner.py -q
```

Expected: PASS.

## Task 2: Persist Model Name

- [x] **Step 1: Write failing repository tests**

Assert `EvidenceRow.model_name` is persisted and legacy evidence tables gain a default `model_name` column.

- [x] **Step 2: Implement storage and migration**

Add `model_name` column, save it, and migrate missing column with `ALTER TABLE`.

- [x] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
python -m mypy src
```

Expected: PASS.

## Task 3: Full Verification And Commit

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: all tests, lint, and typecheck pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan edited files for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```powershell
git add backend/src/debug_agent/experiments/runner.py backend/src/debug_agent/storage/models.py backend/src/debug_agent/storage/repository.py backend/src/debug_agent/storage/database.py backend/tests/experiments/test_runner.py backend/tests/storage/test_repository.py docs/superpowers/plans/2026-06-11-evidence-model-name.md
git commit -m "feat(evidence): persist model name"
```

Expected: one commit containing only Phase 33 changes.

## Self-Review

- Spec coverage: The plan records model names in runtime evidence and persistent evidence rows.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: Uses existing `ModelResponse.model_name`.

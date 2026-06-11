# Model Adapter Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make job execution choose its model adapter from configuration instead of hard-coding `FakeModelAdapter`.

**Architecture:** Add a small `ModelRuntimeSettings` model and a `build_model_adapter()` factory. Default mode remains `fake`, while `ark-seed2-lite` and `ark-seed2-pro` require `ARK_API_KEY` and only construct Ark adapters when explicitly selected.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, mypy.

---

## File Structure

- Modify `backend/src/debug_agent/settings.py`: add `ModelRuntimeSettings` reading `DEBUG_AGENT_MODEL_PROVIDER`.
- Create `backend/src/debug_agent/models/factory.py`: construct `FakeModelAdapter` or `ArkModelAdapter`.
- Modify `backend/src/debug_agent/jobs/service.py`: accept optional model provider and use factory in job execution.
- Create `backend/tests/models/test_factory.py`: cover default fake mode, Ark mode, and invalid provider.
- Modify `backend/tests/jobs/test_service.py`: verify job service calls an injected provider.
- Create `docs/superpowers/plans/2026-06-11-model-adapter-selection.md`: this plan.

## Task 1: Model Adapter Factory

**Files:**
- Modify: `backend/src/debug_agent/settings.py`
- Create: `backend/src/debug_agent/models/factory.py`
- Create: `backend/tests/models/test_factory.py`

- [x] **Step 1: Write failing tests**

Add tests for default fake adapter, Ark lite/pro adapter construction, and invalid provider rejection.

- [x] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/models/test_factory.py -q
```

Expected: FAIL because factory does not exist.

- [x] **Step 3: Implement settings and factory**

Add `ModelRuntimeSettings.from_env()` and `build_model_adapter(case)`.

- [x] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/models/test_factory.py -q
python -m mypy src
```

Expected: PASS.

## Task 2: Job Service Uses Factory

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/tests/jobs/test_service.py`

- [x] **Step 1: Write failing service test**

Add a test proving `DebugJobService` uses an injected model provider.

- [x] **Step 2: Implement service injection**

Accept a callable `model_provider` in `DebugJobService.__init__`, default to `build_model_adapter`, and use it in `_run_claimed_job`.

- [x] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/jobs/test_service.py tests/models/test_factory.py -q
```

Expected: PASS.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/settings.py`
- Create: `backend/src/debug_agent/models/factory.py`
- Modify: `backend/src/debug_agent/jobs/service.py`
- Create: `backend/tests/models/test_factory.py`
- Modify: `backend/tests/jobs/test_service.py`
- Create: `docs/superpowers/plans/2026-06-11-model-adapter-selection.md`

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
git add backend/src/debug_agent/settings.py backend/src/debug_agent/models/factory.py backend/src/debug_agent/jobs/service.py backend/tests/models/test_factory.py backend/tests/jobs/test_service.py docs/superpowers/plans/2026-06-11-model-adapter-selection.md
git commit -m "feat(models): select adapter from runtime settings"
```

Expected: one commit containing only Phase 30 changes.

## Self-Review

- Spec coverage: The plan adds env-driven adapter selection without enabling live calls by default.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: Factory returns the existing `ModelAdapter` protocol.

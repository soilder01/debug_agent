# Job Crop Artifact Directory Implementation Plan

> **For agentic workers:** Use TDD. Runner crop generation must be wired into queued jobs through explicit runtime configuration.

**Goal:** Ensure queued debug jobs generate localized crop artifacts automatically instead of requiring direct `run_experiments()` calls.

**Architecture:** Add `DEBUG_AGENT_IMAGE_ARTIFACT_DIR` to backend settings, pass it into `DebugJobService`, and forward it to `run_experiments()`. Ignore runtime artifact files in git.

**Tech Stack:** FastAPI settings, job service, pytest.

---

### Task 1: Settings and Service Wiring

**Files:**
- Modify: `backend/src/debug_agent/settings.py`
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `.env.example`
- Modify: `.gitignore`
- Test: `backend/tests/test_settings.py`
- Test: `backend/tests/jobs/test_service.py`

- [x] **Step 1: Add failing settings and service tests**

Assert settings expose an image artifact directory and queued jobs write localized crop files when configured.

- [x] **Step 2: Run focused backend tests**

Run: `python -m pytest backend/tests/test_settings.py backend/tests/jobs/test_service.py -q`
Expected: FAIL because settings and service do not wire crop artifact directories yet.

- [x] **Step 3: Implement wiring**

Add settings field/env var, pass it through route-level service construction and service runner calls, and ignore runtime artifacts.

- [x] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests/test_settings.py backend/tests/jobs/test_service.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(jobs): write crop artifacts from queue`.

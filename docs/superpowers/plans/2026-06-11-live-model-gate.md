# Live Model Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Document and test the explicit safety gate for live Ark/Seed model calls.

**Architecture:** Keep default verification fully offline. Add an integration test module that is skipped unless `DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS=1`, `DEBUG_AGENT_MODEL_PROVIDER` selects an Ark provider, and `ARK_API_KEY` is available. Update `.env.example`, model docs, and README with the safe command.

**Tech Stack:** pytest, environment variables, Markdown docs.

---

## File Structure

- Modify `.env.example`: add `DEBUG_AGENT_MODEL_PROVIDER` and `DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS`.
- Modify `docs/model-configuration.md`: document provider values and live test command.
- Modify `README.md`: add safe live model command.
- Create `backend/tests/integration/__init__.py`: package marker.
- Create `backend/tests/integration/test_live_ark_adapter.py`: gated live adapter integration test.
- Create `docs/superpowers/plans/2026-06-11-live-model-gate.md`: this plan.

## Task 1: Gated Integration Test And Docs

**Files:**
- Modify: `.env.example`
- Modify: `docs/model-configuration.md`
- Modify: `README.md`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_live_ark_adapter.py`

- [x] **Step 1: Add gated integration test**

Create a test that skips by default and only calls live Ark when all required env vars are explicitly set.

- [x] **Step 2: Update docs and env template**

Document provider selection, live test gate, and the exact command.

- [x] **Step 3: Run focused integration test in default mode**

Run:

```powershell
python -m pytest tests/integration/test_live_ark_adapter.py -q
```

Expected: skipped.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `.env.example`
- Modify: `docs/model-configuration.md`
- Modify: `README.md`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_live_ark_adapter.py`
- Create: `docs/superpowers/plans/2026-06-11-live-model-gate.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: default test suite passes without live calls.

- [x] **Step 2: Run diagnostics and secret scan**

Scan edited files for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```powershell
git add .env.example docs/model-configuration.md README.md backend/tests/integration/__init__.py backend/tests/integration/test_live_ark_adapter.py docs/superpowers/plans/2026-06-11-live-model-gate.md
git commit -m "test(models): add gated live ark integration"
```

Expected: one commit containing only Phase 32 changes.

## Self-Review

- Spec coverage: The plan protects default CI from live calls and documents how to intentionally enable them.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: Provider values match `ModelRuntimeSettings` and `build_model_adapter`.

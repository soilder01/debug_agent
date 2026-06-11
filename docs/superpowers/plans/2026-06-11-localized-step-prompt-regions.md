# Localized Step Prompt Regions Implementation Plan

> **For agentic workers:** Use TDD. Only add prompt context from known case metadata and observed prediction diffs; do not fabricate coordinates.

**Goal:** Make `localized_observation_request` model calls actually focus on affected answer boxes by adding known box ids and region coordinates to the prompt.

**Architecture:** Before each model call, build a step-specific prompt. Baseline behavior keeps the original prompt. Localized observation compares the golden answer with available case predictions to identify affected boxes, then appends a concise region inspection instruction with known `box_regions`.

**Tech Stack:** Python, pytest.

---

### Task 1: Localized Prompt Augmentation

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] **Step 1: Add failing prompt capture test**

Assert the adapter receives a localized prompt containing the affected box id and known region coordinates.

- [x] **Step 2: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: FAIL because the runner currently sends the original prompt unchanged.

- [x] **Step 3: Implement step prompt builder**

Keep default prompts unchanged, and append localized region instructions only for `localized_observation_request`.

- [x] **Step 4: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(experiments): focus localized prompts on regions`.

# Case Box Region Evidence Implementation Plan

> **For agentic workers:** Use TDD. Do not invent coordinates; only propagate regions explicitly present on the case.

**Goal:** Allow imported/debug cases to carry answer-box region coordinates and have localized evidence attach those regions to image artifacts.

**Architecture:** Add optional `box_regions` metadata to `DebugCase`, keyed by `box_id`. When `localized_observation_request` derives an affected-box artifact, copy the matching case region into the evidence artifact. If a region is missing, keep `region=None`.

**Tech Stack:** Pydantic, pytest.

---

### Task 1: Case Region Contract

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Test: `backend/tests/cases/test_models.py`

- [x] **Step 1: Add failing case model test**

Assert a case can parse `box_regions` with box id, coordinates, unit, and label.

- [x] **Step 2: Run focused case model test**

Run: `python -m pytest backend/tests/cases/test_models.py -q`
Expected: FAIL because `DebugCase` has no `box_regions` field.

- [x] **Step 3: Implement case region models**

Add `BoxRegion` and optional `box_regions` defaulting to an empty list.

- [x] **Step 4: Run focused case model test**

Run: `python -m pytest backend/tests/cases/test_models.py -q`
Expected: PASS.

### Task 2: Localized Evidence Region Propagation

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] **Step 1: Add failing runner test**

Assert localized affected-box artifacts include the matching case region.

- [x] **Step 2: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: FAIL because localized artifacts currently keep `region=None`.

- [x] **Step 3: Implement region propagation**

Build a box-id-to-region map and pass known regions into `ImageArtifact.region`.

- [x] **Step 4: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(evidence): attach case box regions`.

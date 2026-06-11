# Localized Step Image Artifacts Implementation Plan

> **For agentic workers:** Use TDD. This slice must not generate fake crop coordinates or binary files; it only attaches candidate artifact metadata derived from actual failed boxes.

**Goal:** When a localized observation experiment identifies wrong OCR boxes, attach candidate image artifacts to the evidence so humans/agents can see which answer regions need zoom/crop work next.

**Architecture:** In `run_experiments`, after a successful response parse and judge, derive affected box ids from the actual answer diff for `localized_observation_request` steps. If the case has an `image_uri`, add one `ImageArtifact` per affected box with `region=None`, `source_image_uri=case.image_uri`, and an artifact id based on case and box id.

**Tech Stack:** Python, Pydantic, pytest.

---

### Task 1: Runner Artifact Derivation

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] **Step 1: Add failing runner test**

Assert localized observation evidence includes candidate artifacts for mismatched boxes and leaves `region` empty when no coordinates are known.

- [x] **Step 2: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: FAIL because localized evidence currently has no image artifacts.

- [x] **Step 3: Implement artifact derivation**

Use the real answer diff to derive affected box ids only for localized observation steps with a non-empty image URI.

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

Commit with message: `feat(evidence): derive localized image artifacts`.

# Localized Crop Artifacts Implementation Plan

> **For agentic workers:** Use TDD. This slice turns localized image artifact metadata into real local crop files when a safe output directory is provided.

**Goal:** Generate durable crop images for affected OCR answer regions so agents and reviewers can inspect zoomed visual evidence instead of only coordinates.

**Architecture:** Add a local image crop utility backed by Pillow, expose an optional `image_artifact_dir` in `run_experiments`, and populate `derived_image_uri` for localized artifacts when source image URI and region are file-backed.

**Tech Stack:** Python, Pillow, Pydantic, pytest.

---

### Task 1: Runner Crop Generation

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Add: `backend/src/debug_agent/artifacts/images.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/experiments/test_runner.py`

- [x] **Step 1: Add failing crop artifact test**

Assert localized evidence writes a crop file and sets `derived_image_uri` when `image_artifact_dir` is provided.

- [x] **Step 2: Run focused runner test**

Run: `python -m pytest backend/tests/experiments/test_runner.py -q`
Expected: FAIL because `run_experiments` cannot materialize crop files yet.

- [x] **Step 3: Implement local crop generation**

Use Pillow to crop `file://` source images by pixel regions and save deterministic PNG files under the provided artifact directory.

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

Commit with message: `feat(evidence): generate localized crop artifacts`.

# Crop Artifact Preview Implementation Plan

> **For agentic workers:** Use TDD. Generated crop files should be viewable from the UI through a safe backend route, not by exposing arbitrary `file://` paths.

**Goal:** Let operators visually inspect localized crop artifacts directly in Evidence Detail.

**Architecture:** Add a deterministic preview URL to image artifact metadata, serve files from the configured artifact directory through a constrained API route, and render crop previews in the frontend evidence panel.

**Tech Stack:** FastAPI `FileResponse`, Pillow-backed crop artifacts, React, Vitest, pytest.

---

### Task 1: Backend Preview Contract

**Files:**
- Modify: `backend/src/debug_agent/artifacts/images.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `backend/tests/api/test_artifact_images.py`

- [x] **Step 1: Add failing backend preview tests**

Assert materialized crop artifacts carry `preview_image_url` and the backend serves artifact images by filename.

- [x] **Step 2: Run focused backend tests**

Run: `python -m pytest backend/tests/experiments/test_runner.py backend/tests/api/test_artifact_images.py -q`
Expected: FAIL because preview URLs and serving route do not exist.

- [x] **Step 3: Implement preview URL and route**

Set `preview_image_url=/api/artifacts/images/{filename}` for generated crop artifacts and serve only files under `settings.image_artifact_dir`.

- [x] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests/experiments/test_runner.py backend/tests/api/test_artifact_images.py -q`
Expected: PASS.

### Task 2: Frontend Preview Rendering

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] **Step 1: Add failing frontend preview test**

Assert Evidence Detail renders an image preview when an artifact has `preview_image_url`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx`
Expected: FAIL because the component does not render previews yet.

- [x] **Step 3: Implement frontend preview rendering**

Add `preview_image_url` to the type and render an `<img>` with stable alt text.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(evidence): preview crop artifacts`.

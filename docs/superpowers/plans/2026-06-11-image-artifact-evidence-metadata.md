# Image Artifact Evidence Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD for each behavior change. Keep this slice metadata-only; do not implement binary crop generation here.

**Goal:** Make experiment evidence capable of carrying image region/crop artifact metadata so later autonomous OCR debugging can point to wrong-answer areas, zoomed crops, and derived visual evidence.

**Architecture:** Add typed image artifact metadata to `ExperimentEvidence`, persist it as JSON in `EvidenceRow`, migrate legacy SQLite schemas with a default empty list, and render artifacts in the evidence detail UI. The first slice stores metadata only; a later slice will generate actual crop images.

**Tech Stack:** Pydantic, SQLAlchemy, FastAPI serialization, React, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Evidence Contract

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing repository persistence test**

Assert `ExperimentEvidence.image_artifacts` can be saved and restored, including artifact id, kind, source image URI, region coordinates, and derived image URI.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL because evidence has no image artifact contract/persistence.

- [x] **Step 3: Implement metadata model and persistence**

Add typed artifact metadata, `image_artifacts_json`, save/restore mapping, and schema migration defaulting legacy rows to `[]`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 2: Frontend Evidence Detail

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] **Step 1: Add failing component test**

Render an evidence item with image artifacts and assert the region/crop metadata is visible.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx`
Expected: FAIL because the component does not display artifacts yet.

- [x] **Step 3: Implement frontend type and rendering**

Add `image_artifacts` to `ExperimentEvidence` and render artifact kind, source image URI, derived image URI, and region coordinates.

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

Commit with message: `feat(evidence): store image artifact metadata`.

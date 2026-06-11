# Report Image Artifact Summary Implementation Plan

> **For agentic workers:** Use TDD. Keep this slice report/UX only; do not implement crop generation.

**Goal:** Surface image artifact metadata in generated reports so reviewers can quickly tell whether a run produced visual evidence candidates.

**Architecture:** Extend `ExperimentSummary` with `image_artifact_ids`, populate it from `ExperimentRunResult.evidence`, mirror the field in frontend `DebugReport`, and render visual evidence count/ids in `ReportPanel`.

**Tech Stack:** Pydantic, pytest, React, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Report Summary

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [x] **Step 1: Add failing report test**

Assert report experiment summary includes image artifact ids collected from evidence.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/reports/test_generator.py -q`
Expected: FAIL because report summary does not expose image artifacts.

- [x] **Step 3: Implement report summary field**

Add `image_artifact_ids` and populate it from all evidence artifacts.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/reports/test_generator.py -q`
Expected: PASS.

### Task 2: Frontend Report Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] **Step 1: Add failing component test**

Assert report panel displays visual evidence count and artifact ids.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/reports/ReportPanel.test.tsx`
Expected: FAIL because report panel does not render image artifact summary.

- [x] **Step 3: Implement frontend type and rendering**

Add `image_artifact_ids` to `DebugReport.experiment_summary` and render it defensively.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/reports/ReportPanel.test.tsx`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(reports): summarize image artifacts`.

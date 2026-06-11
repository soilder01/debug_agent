# Report Stability Summary Implementation Plan

> **For agentic workers:** Use TDD. Stability metrics must be derived from persisted experiment evidence, not from subjective labels.

**Goal:** Make reports expose model replay stability so low-score or unstable handwriting OCR samples can be triaged automatically.

**Architecture:** Extend `ExperimentSummary` with `failed_trial_count`, `success_rate`, and `stability_label`. Compute labels from evidence scores: `stable_success`, `stable_failure`, `unstable`, and `not_run`. Mirror the contract in the frontend report panel.

**Tech Stack:** Pydantic, pytest, React, TypeScript, Vitest.

---

### Task 1: Backend Stability Summary

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [x] **Step 1: Add failing backend stability test**

Assert mixed evidence scores produce `failed_trial_count`, `success_rate`, and `stability_label=unstable`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/reports/test_generator.py -q`
Expected: FAIL because report summaries do not include stability metrics.

- [x] **Step 3: Implement backend stability metrics**

Compute metrics from `run_result.evidence` and include them in `ExperimentSummary`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/reports/test_generator.py -q`
Expected: PASS.

### Task 2: Frontend Stability Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] **Step 1: Add failing frontend stability test**

Assert `ReportPanel` displays success rate, failed trials, and stability label.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/reports/ReportPanel.test.tsx`
Expected: FAIL because the panel does not render stability metrics.

- [x] **Step 3: Implement frontend stability rendering**

Add the new fields to the report type and render them defensively.

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

Commit with message: `feat(reports): summarize replay stability`.

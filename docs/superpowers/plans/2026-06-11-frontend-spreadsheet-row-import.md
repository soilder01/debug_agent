# Frontend Spreadsheet Row Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Expose the spreadsheet-row sync API in the frontend so operators can paste row JSON and create five-replay debug jobs.

**Architecture:** Add a typed API client for `POST /imports/spreadsheet-rows`, then add an App panel that parses JSON array input, submits rows, shows imported/rejected row results, and refreshes the batch job summary.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Frontend Spreadsheet Import Flow

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing App test**

Add a test that enters spreadsheet rows JSON, clicks `Import spreadsheet rows JSON`, and expects a `POST /api/imports/spreadsheet-rows` request plus imported-row UI.

- [x] **Step 2: Run frontend App test for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the UI and client do not exist.

- [x] **Step 3: Implement minimal client and App UI**

Add `importSpreadsheetRows()` and a small panel in `App.tsx` following existing JSONL/CSV import behavior.

- [x] **Step 4: Run frontend App test for GREEN**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(frontend): import spreadsheet rows`.

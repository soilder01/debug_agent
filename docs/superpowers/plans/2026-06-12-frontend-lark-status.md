# Frontend Lark Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Let operators check Lark spreadsheet configuration and connectivity from the frontend before syncing rows.

**Architecture:** Add `fetchLarkSpreadsheetStatus(checkConnectivity)` to the API client, store status in `App`, and render a status action/result inside the Spreadsheet Sync section.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Lark Status UI

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing UI test**

Add a test proving clicking `Check Lark status` calls `/api/spreadsheets/lark/status?check_connectivity=true` and renders configured/connectivity details.

- [x] **Step 2: Run frontend test for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the status button and client are missing.

- [x] **Step 3: Implement status UI**

Add client type/function, App state/action, and Spreadsheet Sync status rendering.

- [x] **Step 4: Run frontend test for GREEN**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused frontend tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/jobs/JobStatusPanel.test.tsx`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(frontend): show lark spreadsheet status`.

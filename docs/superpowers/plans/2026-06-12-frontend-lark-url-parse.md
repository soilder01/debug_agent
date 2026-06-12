# Frontend Lark URL Parse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Let operators paste a Lark spreadsheet URL and automatically populate `spreadsheet_id` and `sheet_id` for sync.

**Architecture:** Keep parsing local to `App` for this small UI feature. Parse `/sheets/{spreadsheet_id}?sheet={sheet_id}` links with `URL`, update both controlled sync fields, and show a user-friendly error when the pasted value is not a Lark sheet URL.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Lark URL Parsing UI

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing UI test**

Add a test proving that pasting `https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX` and clicking `Use spreadsheet URL` populates the sync fields.

- [x] **Step 2: Run frontend test for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the URL input and parse action are missing.

- [x] **Step 3: Implement URL parsing**

Add `spreadsheetUrl` state, render a URL input, and add a `useSpreadsheetUrl()` function that parses the path and `sheet` query param.

- [x] **Step 4: Run frontend test for GREEN**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/jobs/JobStatusPanel.test.tsx`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(frontend): parse lark sheet urls`.

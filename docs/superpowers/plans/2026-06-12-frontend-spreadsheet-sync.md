# Frontend Spreadsheet Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Let operators trigger configured spreadsheet synchronization from the frontend and immediately triage the created debug jobs.

**Architecture:** Add a typed frontend client for `POST /spreadsheets/sync`, then add a small form in `App` for `spreadsheet_id` and `sheet_id`. Reuse the existing batch job triage state so synced rows appear in the same job queue UI used by JSONL/CSV/spreadsheet-row imports.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Spreadsheet Sync UI

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing UI test**

Add a test proving the UI posts `spreadsheet_id`, `sheet_id`, `create_jobs: true`, and `baseline_trials: 5` to `/api/spreadsheets/sync`, renders imported rows/rejections, and puts created jobs into the batch triage list.

- [x] **Step 2: Run frontend test for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the sync form and client method are missing.

- [x] **Step 3: Implement frontend client and UI**

Add `syncSpreadsheetRows(spreadsheetId, sheetId)` to `frontend/src/api/client.ts`.

Add state and form fields in `frontend/src/app/App.tsx`:

```tsx
const [spreadsheetId, setSpreadsheetId] = useState("");
const [sheetId, setSheetId] = useState("");
const [spreadsheetSyncResult, setSpreadsheetSyncResult] = useState<SpreadsheetSyncResponse | null>(null);
```

When sync succeeds, set `batchResult`, `jobListSummaryLabel`, `jobListTotalCount`, and `batchJobStatuses` from returned jobs.

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

Commit with message: `feat(frontend): sync spreadsheets`.

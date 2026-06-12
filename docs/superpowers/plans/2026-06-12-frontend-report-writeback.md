# Frontend Report Writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Let operators trigger spreadsheet writeback from a loaded persisted job report.

**Architecture:** Add a typed `writeJobReportToSpreadsheet(jobId, reportUrl)` frontend client for `POST /jobs/{job_id}/spreadsheet-writeback`. In `App`, render a writeback action only when a report with `job_id` is loaded, call the endpoint with a stable API report URL, and display the returned row id and field values.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Frontend Report Writeback Action

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing UI tests**

Add a test proving that after loading a persisted report, clicking `Write report to spreadsheet` posts to `/api/jobs/{job_id}/spreadsheet-writeback` with a report URL and renders the returned row id and fields.

- [x] **Step 2: Run frontend tests for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the writeback button and client method are missing.

- [x] **Step 3: Implement frontend client and UI wiring**

Add:

```typescript
export type SpreadsheetWritebackResult = {
  row_id: string;
  fields: Record<string, string>;
};

export async function writeJobReportToSpreadsheet(jobId: string, reportUrl: string): Promise<SpreadsheetWritebackResult> {
  const response = await fetch(`/api/jobs/${jobId}/spreadsheet-writeback`, {
    body: JSON.stringify({ report_url: reportUrl }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to write job report ${jobId}: ${response.status}`);
  }
  return (await response.json()) as SpreadsheetWritebackResult;
}
```

Add App state:

```typescript
const [spreadsheetWritebackResult, setSpreadsheetWritebackResult] = useState<SpreadsheetWritebackResult | null>(null);
```

Render the action and result near `ReportPanel`.

- [x] **Step 4: Run frontend tests for GREEN**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/reports/ReportPanel.test.tsx`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(frontend): write reports to spreadsheets`.

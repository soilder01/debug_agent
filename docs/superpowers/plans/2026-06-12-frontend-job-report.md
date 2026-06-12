# Frontend Job Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Let operators load and inspect a persisted debug report directly from an existing job.

**Architecture:** Add a typed `fetchJobReport(jobId)` frontend API client and expose a `Load persisted report` action in `JobStatusPanel`. Wire `App` to call the new API, store the returned `DebugReport`, and reuse the existing `CaseDetail`, `ExperimentTimeline`, `EvidenceDetail`, and `ReportPanel` rendering path.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Frontend Job Report Loading

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/jobs/JobStatusPanel.tsx`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/jobs/JobStatusPanel.test.tsx`

- [x] **Step 1: Add failing UI tests**

Add tests proving the job panel renders a `Load persisted report` action and `App` calls `/api/jobs/{job_id}/report`, then renders the returned root-cause report.

- [x] **Step 2: Run frontend tests for RED**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/jobs/JobStatusPanel.test.tsx`
Expected: FAIL because the button and client method are missing.

- [x] **Step 3: Implement frontend client and wiring**

Add:

```typescript
export async function fetchJobReport(jobId: string): Promise<DebugReport> {
  const response = await fetch(`/api/jobs/${jobId}/report`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job report ${jobId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}
```

Update `JobStatusPanel` props:

```typescript
type JobStatusPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  onSelectEvidence?: (evidenceId: string) => void;
  onLoadReport?: () => void;
};
```

Render:

```tsx
<button type="button" onClick={onLoadReport}>
  Load persisted report
</button>
```

Add `loadCurrentJobReport()` in `App` and pass it to `JobStatusPanel`.

- [x] **Step 4: Run frontend tests for GREEN**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/jobs/JobStatusPanel.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx src/jobs/JobStatusPanel.test.tsx src/reports/ReportPanel.test.tsx`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(frontend): load persisted job reports`.

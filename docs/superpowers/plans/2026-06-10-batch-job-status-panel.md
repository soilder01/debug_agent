# Batch Job Status Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show per-job status for batch submissions and poll each created batch job until it reaches a terminal state.

**Architecture:** Reuse the existing `GET /jobs/{job_id}` status endpoint and the existing `fetchJobStatus()` client. The frontend stores a map of batch job statuses keyed by `job_id`, renders a compact list for created batch jobs, and polls non-terminal batch jobs independently from the single-job panel.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, existing FastAPI job status API.

---

## File Structure

- Modify `frontend/src/app/App.test.tsx`: add a failing frontend test that submits two batch jobs, verifies the batch API payload, verifies initial created states, and verifies polling updates each job to terminal state.
- Modify `frontend/src/app/App.tsx`: add `batchJobStatuses` state, batch polling effect, and render a per-job status list below the batch summary.
- No backend changes: this phase intentionally reuses `POST /debug-jobs/batch` and `GET /jobs/{job_id}`.

## Task 1: Frontend Batch Status Polling

**Files:**
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Write the failing test**

Add this test after the existing batch summary test in `frontend/src/app/App.test.tsx`:

```typescript
  it("polls and renders statuses for batch debug jobs", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              { job_id: "job-1", case_id: "handwrite233", status: "created" },
              { job_id: "job-2", case_id: "handwrite233", status: "created" }
            ],
            rejected_case_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-2",
            case_id: "handwrite233",
            status: "failed",
            attempt_count: 2,
            error_message: "fixture failed",
            evidence_ids: []
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));

    expect(await screen.findByText("批量创建：2")).toBeInTheDocument();
    expect(screen.getByText("job-1：created")).toBeInTheDocument();
    expect(screen.getByText("job-2：created")).toBeInTheDocument();
    expect(await screen.findByText("job-1：completed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(await screen.findByText("job-2：failed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("job-2 错误：fixture failed")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-2");
  });
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because the app does not render per-batch-job statuses or poll batch jobs yet.

- [ ] **Step 3: Implement minimal batch status state and polling**

In `frontend/src/app/App.tsx`, update state near the existing batch state:

```typescript
  const [batchCaseIds, setBatchCaseIds] = useState("");
  const [batchResult, setBatchResult] = useState<BatchDebugJobResponse | null>(null);
  const [batchJobStatuses, setBatchJobStatuses] = useState<Record<string, DebugJobStatus | SubmittedDebugJob>>({});
```

Add this effect after the existing single-job polling effect:

```typescript
  useEffect(() => {
    const pendingJobs = Object.values(batchJobStatuses).filter(
      (job) => job.status !== "completed" && job.status !== "failed"
    );
    if (pendingJobs.length === 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      for (const job of pendingJobs) {
        fetchJobStatus(job.job_id)
          .then((status) => {
            setBatchJobStatuses((current) => ({ ...current, [status.job_id]: status }));
          })
          .catch((caught: unknown) => {
            setError(caught instanceof Error ? caught.message : "Unknown error");
          });
      }
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [batchJobStatuses]);
```

Update `submitBatchJobs()` to initialize the status map:

```typescript
  async function submitBatchJobs() {
    setError("");
    const caseIds = batchCaseIds
      .split(/\s+/)
      .map((caseId) => caseId.trim())
      .filter(Boolean);
    try {
      const result = await submitBatchDebugJobs(caseIds);
      setBatchResult(result);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }
```

Render the status list below the current batch summary:

```tsx
            {Object.values(batchJobStatuses).length > 0 ? (
              <ul aria-label="Batch job statuses">
                {Object.values(batchJobStatuses).map((job) => (
                  <li key={job.job_id}>
                    <span>
                      {job.job_id}：{job.status}
                    </span>
                    {job.error_message ? <span> {job.job_id} 错误：{job.error_message}</span> : null}
                  </li>
                ))}
              </ul>
            ) : null}
```

- [ ] **Step 4: Run the focused frontend test to verify it passes**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS with 3 frontend tests.

- [ ] **Step 5: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected:
- Backend tests pass.
- Frontend tests pass.
- Backend lint passes.
- Frontend lint passes.
- Backend typecheck passes.
- Frontend typecheck passes.

- [ ] **Step 6: Secret scan**

Run:

```powershell
git diff --cached; git diff
```

Expected: no `ARK_API_KEY` value and no token matching `ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` appears in the diff.

- [ ] **Step 7: Commit**

Run:

```powershell
git add frontend/src/app/App.test.tsx frontend/src/app/App.tsx docs/superpowers/plans/2026-06-10-batch-job-status-panel.md
git commit -m "feat(frontend): show batch job statuses"
```

Expected: one commit containing only the Phase 14 frontend batch status changes and plan.

## Self-Review

- Spec coverage: This plan covers per-job batch status rendering, reuse of existing status API, and independent polling until terminal state.
- Placeholder scan: No TBD, TODO, or unspecified implementation steps remain.
- Type consistency: The plan uses existing `BatchDebugJobResponse`, `DebugJobStatus`, `SubmittedDebugJob`, and `fetchJobStatus()` names exactly as defined in `frontend/src/api/client.ts`.

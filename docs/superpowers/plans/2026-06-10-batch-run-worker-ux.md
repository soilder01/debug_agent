# Batch Run Worker UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make batch submission flow directly actionable by adding a one-click "start worker for this batch" button and visible batch completion progress.

**Architecture:** Reuse the existing frontend worker API client and batch job polling. Add derived batch progress counts from `batchJobStatuses`, and add a batch-local action button that calls the same `startWorker()` handler used by the global worker panel. No backend changes are needed.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/app/App.test.tsx`: add behavior coverage for batch submission, batch worker start, and progress rendering.
- Modify `frontend/src/app/App.tsx`: add derived batch progress and a `Start worker for batch` button in the Batch Jobs section.
- Create `docs/superpowers/plans/2026-06-10-batch-run-worker-ux.md`: this plan.

## Task 1: Batch Worker Start And Progress UI

**Files:**
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Write failing test**

Add this test to `frontend/src/app/App.test.tsx`:

```typescript
  it("starts the worker from the batch section and renders batch progress", async () => {
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
            running: true,
            processed_count: 0,
            error_count: 0,
            last_error: null
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
            status: "running",
            attempt_count: 1,
            error_message: null,
            evidence_ids: []
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            running: true,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));
    await userEvent.click(await screen.findByRole("button", { name: "Start worker for batch" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("批量进度：0/2")).toBeInTheDocument();
    expect(await screen.findByText("批量进度：1/2", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("Worker running：true")).toBeInTheDocument();
    expect(screen.getByText("Worker processed：1")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because `Start worker for batch` and `批量进度` are not rendered yet.

- [ ] **Step 3: Add derived batch progress**

In `frontend/src/app/App.tsx`, after state declarations add:

```typescript
  const batchJobs = Object.values(batchJobStatuses);
  const completedBatchJobs = batchJobs.filter((job) => job.status === "completed").length;
```

Replace repeated `Object.values(batchJobStatuses)` usages in render and polling with `batchJobs` where practical.

- [ ] **Step 4: Add batch-local worker button and progress**

In the Batch Jobs section, after rejected case text, add:

```tsx
            <p>
              批量进度：{completedBatchJobs}/{batchResult.jobs.length}
            </p>
            <button type="button" onClick={startWorkerLoop}>
              Start worker for batch
            </button>
```

- [ ] **Step 5: Run focused frontend tests**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS with 5 tests.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-10-batch-run-worker-ux.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [ ] **Step 2: Run diagnostics**

Run diagnostics for:
- `frontend/src/app/App.tsx`
- `frontend/src/app/App.test.tsx`

Expected: no diagnostics.

- [ ] **Step 3: Secret scan**

Run:

```powershell
git diff -- frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-batch-run-worker-ux.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no real secret values.

- [ ] **Step 4: Commit**

Run:

```powershell
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-batch-run-worker-ux.md
git commit -m "feat(frontend): streamline batch worker flow"
```

Expected: one commit containing only Phase 19 batch worker UX changes and plan.

## Self-Review

- Spec coverage: The plan adds a batch-local worker start action and visible batch completion progress.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: The plan reuses existing `startWorkerLoop`, `batchJobStatuses`, and `WorkerStatus` fields exactly as currently defined.

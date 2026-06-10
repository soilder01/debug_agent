# Frontend Worker Control Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend control panel for starting, stopping, and observing the backend async worker.

**Architecture:** Extend the existing frontend API client with worker control calls that mirror `GET /worker/status`, `POST /worker/start`, and `POST /worker/stop`. Add a small worker section inside `App` that renders lifecycle state and polls status while the worker is running, without changing existing single-job or batch-job flows.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, existing FastAPI worker control API.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add `WorkerStatus` type plus `fetchWorkerStatus()`, `startWorker()`, and `stopWorker()`.
- Modify `frontend/src/app/App.tsx`: add worker status state, start/stop handlers, running-status polling, and a worker control section.
- Modify `frontend/src/app/App.test.tsx`: add TDD coverage for start, status polling, and stop.
- Create `docs/superpowers/plans/2026-06-10-frontend-worker-control-panel.md`: this plan.

## Task 1: Worker API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Write failing frontend test**

Add this test to `frontend/src/app/App.test.tsx`:

```typescript
  it("starts, polls, and stops the worker from the UI", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
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
            running: true,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            running: false,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Start worker" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("Worker running：true")).toBeInTheDocument();
    expect(await screen.findByText("Worker processed：1", {}, { timeout: 500 })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Stop worker" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/stop", { method: "POST" });
    expect(await screen.findByText("Worker running：false")).toBeInTheDocument();
    expect(screen.getByText("Worker errors：0")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run the frontend test to verify failure**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because the worker buttons and API client functions do not exist yet.

- [ ] **Step 3: Add worker API client functions**

In `frontend/src/api/client.ts`, add:

```typescript
export type WorkerStatus = {
  running: boolean;
  processed_count: number;
  error_count: number;
  last_error: string | null;
};
```

Add:

```typescript
export async function fetchWorkerStatus(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/status");
  if (!response.ok) {
    throw new Error(`Failed to fetch worker status: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}

export async function startWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/start", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to start worker: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}

export async function stopWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/stop", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to stop worker: ${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}
```

- [ ] **Step 4: Add worker UI and polling**

In `frontend/src/app/App.tsx`, import the new client functions and `WorkerStatus`. Add worker status state:

```typescript
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
```

Add a `useEffect` that polls `fetchWorkerStatus()` every 100ms while `workerStatus?.running` is true.

Add handlers:

```typescript
  async function startWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await startWorker());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function stopWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await stopWorker());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }
```

Render a `Worker` section with `Start worker` and `Stop worker` buttons and the following text when status exists:

```tsx
          <p>Worker running：{String(workerStatus.running)}</p>
          <p>Worker processed：{workerStatus.processed_count}</p>
          <p>Worker errors：{workerStatus.error_count}</p>
          {workerStatus.last_error ? <p role="alert">Worker error：{workerStatus.last_error}</p> : null}
```

- [ ] **Step 5: Run focused frontend tests**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS with 4 tests.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-10-frontend-worker-control-panel.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [ ] **Step 2: Run diagnostics**

Run diagnostics for:
- `frontend/src/api/client.ts`
- `frontend/src/app/App.tsx`
- `frontend/src/app/App.test.tsx`

Expected: no diagnostics.

- [ ] **Step 3: Secret scan**

Run:

```powershell
git diff -- frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-frontend-worker-control-panel.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no matches except literal scan instructions if present.

- [ ] **Step 4: Commit**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-frontend-worker-control-panel.md
git commit -m "feat(frontend): add worker control panel"
```

Expected: one commit containing only Phase 18 frontend worker control changes and plan.

## Self-Review

- Spec coverage: The plan exposes worker start, stop, status display, and polling in the frontend.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: The plan uses backend response fields `running`, `processed_count`, `error_count`, and `last_error` exactly as implemented.

# Frontend JSONL Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend JSONL import entry point that imports pasted `DebugCase` JSONL and creates debug jobs.

**Architecture:** Extend the existing frontend API client with `importJsonlCases()`, then add a compact import section to `App`. Successful imports reuse the existing batch job state map so imported jobs immediately appear in the current batch status/progress UI and can be processed by the existing worker controls.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add `JsonlImportResponse` and `importJsonlCases()`.
- Modify `frontend/src/app/App.tsx`: add JSONL textarea, submit handler, imported/rejected summary, and reuse `batchJobStatuses`.
- Modify `frontend/src/app/App.test.tsx`: add frontend behavior coverage for JSONL import.
- Create `docs/superpowers/plans/2026-06-10-frontend-jsonl-import.md`: this plan.

## Task 1: JSONL Import API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

Add this test to `frontend/src/app/App.test.tsx`:

```typescript
  it("imports JSONL cases and renders created jobs in the batch area", async () => {
    const jsonl = "{\"case_id\":\"imported-jsonl-1\"}";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["imported-jsonl-1"],
          jobs: [{ job_id: "job-imported-1", case_id: "imported-jsonl-1", status: "created" }],
          rejected_lines: []
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.type(screen.getByLabelText("JSONL cases"), jsonl);
    await userEvent.click(screen.getByRole("button", { name: "Import JSONL cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/jsonl", {
      body: JSON.stringify({ jsonl, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("job-imported-1：created")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because `JSONL cases` textarea and `Import JSONL cases` button do not exist.

- [ ] **Step 3: Add API client type and function**

In `frontend/src/api/client.ts`, add:

```typescript
export type JsonlRejectedLine = {
  line_number: number;
  error_message: string;
};

export type JsonlImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_lines: JsonlRejectedLine[];
};
```

Add:

```typescript
export async function importJsonlCases(jsonl: string, createJobs = true): Promise<JsonlImportResponse> {
  const response = await fetch("/api/imports/jsonl", {
    body: JSON.stringify({ jsonl, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to import JSONL cases: ${response.status}`);
  }
  return (await response.json()) as JsonlImportResponse;
}
```

- [ ] **Step 4: Run frontend test to confirm it still fails on UI**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because App does not render the import section yet.

## Task 2: JSONL Import UI

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Add App state and handler**

In `frontend/src/app/App.tsx`, import `importJsonlCases` and `JsonlImportResponse`.

Add state:

```typescript
  const [jsonlCases, setJsonlCases] = useState("");
  const [jsonlImportResult, setJsonlImportResult] = useState<JsonlImportResponse | null>(null);
```

Add handler:

```typescript
  async function importJsonl() {
    setError("");
    try {
      const result = await importJsonlCases(jsonlCases);
      setJsonlImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }
```

- [ ] **Step 2: Add import section UI**

In `frontend/src/app/App.tsx`, render a section before Batch Jobs:

```tsx
      <section>
        <h2>JSONL Import</h2>
        <label htmlFor="jsonl-cases">JSONL cases</label>
        <textarea
          id="jsonl-cases"
          value={jsonlCases}
          onChange={(event) => setJsonlCases(event.target.value)}
        />
        <button type="button" onClick={importJsonl}>
          Import JSONL cases
        </button>
        {jsonlImportResult ? (
          <>
            <p>导入样本：{jsonlImportResult.imported_case_ids.length}</p>
            <p>
              导入拒绝：
              {jsonlImportResult.rejected_lines.length === 0
                ? "无"
                : jsonlImportResult.rejected_lines
                    .map((line) => `${line.line_number}:${line.error_message}`)
                    .join(", ")}
            </p>
          </>
        ) : null}
      </section>
```

- [ ] **Step 3: Run frontend tests**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS with 6 tests.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-10-frontend-jsonl-import.md`

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
git diff -- frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-frontend-jsonl-import.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no real secret values.

- [ ] **Step 4: Commit**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-frontend-jsonl-import.md
git commit -m "feat(frontend): add jsonl import panel"
```

Expected: one commit containing only Phase 21 frontend JSONL import changes and plan.

## Self-Review

- Spec coverage: The plan adds a frontend JSONL import path and reuses batch job status/progress UI.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Uses backend response fields `imported_case_ids`, `jobs`, and `rejected_lines` exactly as implemented.

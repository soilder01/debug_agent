# Frontend CSV Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a frontend CSV import panel that submits CSV rows to `/api/imports/csv` and feeds created jobs into the existing batch job status workflow.

**Architecture:** Mirror the JSONL import client and UI so CSV imports reuse the existing `BatchDebugJobResponse` and batch polling state. Keep the CSV contract owned by the backend; the frontend only transports raw CSV text, renders imported count, renders rejected rows, and hydrates the batch status panel from returned jobs.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add CSV import response types and `importCsvCases`.
- Modify `frontend/src/app/App.tsx`: add CSV textarea, import handler, summary rendering, and batch state hydration.
- Modify `frontend/src/app/App.test.tsx`: add a focused test for CSV import request shape and UI integration.
- Create `docs/superpowers/plans/2026-06-10-frontend-csv-import.md`: this plan.

## Task 1: API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Write the failing app test**

Append this test inside `describe("App", () => { ... })` in `frontend/src/app/App.test.tsx`:

```typescript
  it("imports CSV cases and renders created jobs in the batch area", async () => {
    const csvText = "case_id,image_uri,prompt,golden_answer_json,scoring_standard,predictions_json,avg_score\n";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["csv-import-1"],
          jobs: [{ job_id: "job-csv-1", case_id: "csv-import-1", status: "created" }],
          rejected_rows: []
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText("CSV cases"), { target: { value: csvText } });
    await userEvent.click(screen.getByRole("button", { name: "Import CSV cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/csv", {
      body: JSON.stringify({ csv_text: csvText, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("job-csv-1：created")).toBeInTheDocument();
  });
```

- [x] **Step 2: Run the test to verify failure**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because the CSV textarea/button do not exist.

- [x] **Step 3: Add CSV types and client**

In `frontend/src/api/client.ts`, add these types near the JSONL import types:

```typescript
export type CsvRejectedRow = {
  row_number: number;
  error_message: string;
};

export type CsvImportResponse = {
  imported_case_ids: string[];
  jobs: SubmittedDebugJob[];
  rejected_rows: CsvRejectedRow[];
};
```

Add this function after `importJsonlCases`:

```typescript
export async function importCsvCases(csvText: string, createJobs = true): Promise<CsvImportResponse> {
  const response = await fetch("/api/imports/csv", {
    body: JSON.stringify({ csv_text: csvText, create_jobs: createJobs }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to import CSV cases: ${response.status}`);
  }
  return (await response.json()) as CsvImportResponse;
}
```

- [x] **Step 4: Run frontend typecheck to verify the client compiles**

Run:

```powershell
npx --yes pnpm@9.15.4 typecheck
```

Expected: PASS.

## Task 2: CSV Import UI

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Import CSV client symbols**

Update the import list in `frontend/src/app/App.tsx` to include:

```typescript
  importCsvCases,
  type CsvImportResponse,
```

- [x] **Step 2: Add CSV state and handler**

Add state next to the JSONL state:

```typescript
  const [csvCases, setCsvCases] = useState("");
  const [csvImportResult, setCsvImportResult] = useState<CsvImportResponse | null>(null);
```

Add this handler after `importJsonl`:

```typescript
  async function importCsv() {
    setError("");
    try {
      const result = await importCsvCases(csvCases);
      setCsvImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }
```

- [x] **Step 3: Add CSV import section**

Insert this section after the JSONL import section in `frontend/src/app/App.tsx`:

```tsx
      <section>
        <h2>CSV Import</h2>
        <label htmlFor="csv-cases">CSV cases</label>
        <textarea
          id="csv-cases"
          value={csvCases}
          onChange={(event) => setCsvCases(event.target.value)}
        />
        <button type="button" onClick={importCsv}>
          Import CSV cases
        </button>
        {csvImportResult ? (
          <>
            <p>CSV 导入样本：{csvImportResult.imported_case_ids.length}</p>
            <p>
              CSV 导入拒绝：
              {csvImportResult.rejected_rows.length === 0
                ? "无"
                : csvImportResult.rejected_rows
                    .map((row) => `${row.row_number}:${row.error_message}`)
                    .join(", ")}
            </p>
          </>
        ) : null}
      </section>
```

- [x] **Step 4: Run the app test**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS with the new CSV import test and existing tests.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-10-frontend-csv-import.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics**

Run diagnostics for edited frontend files.

Expected: no diagnostics.

- [x] **Step 3: Secret scan**

Run:

```powershell
Select-String -Path frontend/src/api/client.ts,frontend/src/app/App.tsx,frontend/src/app/App.test.tsx,docs/superpowers/plans/2026-06-10-frontend-csv-import.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no output.

- [x] **Step 4: Commit**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-10-frontend-csv-import.md
git commit -m "feat(frontend): add csv import panel"
```

Expected: one commit containing only Phase 23 CSV frontend import changes and plan.

## Self-Review

- Spec coverage: The plan adds a CSV client, CSV UI, rejected row rendering, and batch status hydration.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Uses backend response fields `imported_case_ids`, `jobs`, and `rejected_rows`; frontend request uses `csv_text` and `create_jobs`.

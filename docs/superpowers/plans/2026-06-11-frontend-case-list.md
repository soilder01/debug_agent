# Frontend Case List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a frontend imported case list panel backed by `GET /api/cases`.

**Architecture:** Extend the frontend API client with lightweight case summary types and `fetchCases()`. Add a panel in `App.tsx` that loads imported case summaries on demand, displays key debug fields, and lets users copy the case ids into the existing batch submission textarea.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add `DebugCaseSummary`, `DebugCaseListResponse`, and `fetchCases()`.
- Modify `frontend/src/app/App.tsx`: add state, load handler, and imported case list UI.
- Modify `frontend/src/app/App.test.tsx`: add a focused case list interaction test.
- Create `docs/superpowers/plans/2026-06-11-frontend-case-list.md`: this plan.

## Task 1: API Client And UI Test

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Write failing app test**

Append this test inside `describe("App", () => { ... })` in `frontend/src/app/App.test.tsx`:

```typescript
  it("loads imported case summaries and can copy them into batch submission", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          cases: [
            {
              case_id: "case-list-1",
              image_uri: "file://case-list-1.png",
              avg_score: 0.2,
              debug_status: "pending",
              root_cause: "visual_recognition_failure"
            },
            {
              case_id: "case-list-2",
              image_uri: "file://case-list-2.png",
              avg_score: 1,
              debug_status: "",
              root_cause: ""
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases");
    expect(await screen.findByText("已导入样本：2")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜avg_score 0.2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.getByText("case-list-2｜avg_score 1｜未标记｜未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Use imported cases for batch" }));

    expect(screen.getByLabelText("Batch case ids")).toHaveValue("case-list-1\ncase-list-2");
  });
```

- [x] **Step 2: Run test to verify failure**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because `Load imported cases` does not exist.

- [x] **Step 3: Add frontend API client**

In `frontend/src/api/client.ts`, add these types after `BatchDebugJobResponse`:

```typescript
export type DebugCaseSummary = {
  case_id: string;
  image_uri: string;
  avg_score: number;
  debug_status: string;
  root_cause: string;
};

export type DebugCaseListResponse = {
  cases: DebugCaseSummary[];
};
```

Add this function after `submitBatchDebugJobs`:

```typescript
export async function fetchCases(): Promise<DebugCaseListResponse> {
  const response = await fetch("/api/cases");
  if (!response.ok) {
    throw new Error(`Failed to fetch imported cases: ${response.status}`);
  }
  return (await response.json()) as DebugCaseListResponse;
}
```

- [x] **Step 4: Run frontend typecheck**

Run:

```powershell
npx --yes pnpm@9.15.4 typecheck
```

Expected: PASS.

## Task 2: Imported Case List UI

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Import client symbols**

Update `frontend/src/app/App.tsx` imports to include:

```typescript
  type DebugCaseSummary,
  fetchCases,
```

- [x] **Step 2: Add state and handlers**

Add state near batch state:

```typescript
  const [importedCases, setImportedCases] = useState<DebugCaseSummary[]>([]);
```

Add handlers before `submitBatchJobs`:

```typescript
  async function loadImportedCases() {
    setError("");
    try {
      const result = await fetchCases();
      setImportedCases(result.cases);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  function useImportedCasesForBatch() {
    setBatchCaseIds(importedCases.map((caseSummary) => caseSummary.case_id).join("\n"));
  }
```

- [x] **Step 3: Add case list section**

Insert this section before `Batch Jobs`:

```tsx
      <section>
        <h2>Imported Cases</h2>
        <button type="button" onClick={loadImportedCases}>
          Load imported cases
        </button>
        {importedCases.length > 0 ? (
          <>
            <p>已导入样本：{importedCases.length}</p>
            <button type="button" onClick={useImportedCasesForBatch}>
              Use imported cases for batch
            </button>
            <ul aria-label="Imported case summaries">
              {importedCases.map((caseSummary) => (
                <li key={caseSummary.case_id}>
                  {caseSummary.case_id}｜avg_score {caseSummary.avg_score}｜
                  {caseSummary.debug_status || "未标记"}｜{caseSummary.root_cause || "未归因"}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
```

- [x] **Step 4: Run app tests**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: PASS.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-11-frontend-case-list.md`

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
Select-String -Path frontend/src/api/client.ts,frontend/src/app/App.tsx,frontend/src/app/App.test.tsx,docs/superpowers/plans/2026-06-11-frontend-case-list.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no output.

- [x] **Step 4: Commit**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-case-list.md
git commit -m "feat(frontend): show imported case list"
```

Expected: one commit containing only Phase 26 frontend case list changes and plan.

## Self-Review

- Spec coverage: The plan adds API client support, a visible imported cases panel, batch handoff, focused tests, and full verification.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Frontend fields match backend `GET /cases` response fields from Phase 25.

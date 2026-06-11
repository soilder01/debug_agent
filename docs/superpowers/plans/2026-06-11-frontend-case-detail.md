# Frontend Case Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let users open full imported case details from the frontend Imported Cases panel.

**Architecture:** Add a typed frontend client for `GET /api/cases/{case_id}`. Reuse the existing Imported Cases list and add per-case detail buttons that fetch and render prompt, image URI, scoring standard, golden answers, predictions, and human notes.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add `DebugCaseDetail` type and `fetchCaseDetail(caseId)`.
- Modify `frontend/src/app/App.tsx`: add selected case detail state, fetch handler, and detail panel.
- Modify `frontend/src/app/App.test.tsx`: add a focused interaction test for case detail loading.
- Create `docs/superpowers/plans/2026-06-11-frontend-case-detail.md`: this plan.

## Task 1: Frontend Case Detail Client And UI

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Write failing test**

Append a test to `frontend/src/app/App.test.tsx` that first loads imported cases, then clicks `View case detail case-list-1`, and verifies `/api/cases/case-list-1` is fetched and rendered.

- [x] **Step 2: Run failing test**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because the detail button and client do not exist.

- [x] **Step 3: Implement client and UI**

Add `DebugCaseDetail` and `fetchCaseDetail()` to `frontend/src/api/client.ts`, then add selected-case state and detail rendering to `frontend/src/app/App.tsx`.

- [x] **Step 4: Run focused tests**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
npx --yes pnpm@9.15.4 typecheck
```

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-11-frontend-case-detail.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics for edited files and scan these paths for committed Ark key patterns:

```powershell
Select-String -Path frontend/src/api/client.ts,frontend/src/app/App.tsx,frontend/src/app/App.test.tsx,docs/superpowers/plans/2026-06-11-frontend-case-detail.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no diagnostics and no secret matches.

- [x] **Step 3: Commit**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-case-detail.md
git commit -m "feat(frontend): show case detail"
```

Expected: one commit containing only Phase 28 frontend case detail changes and plan.

## Self-Review

- Spec coverage: The plan covers detail client, UI drilldown, tests, verification, scan, and commit.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: Detail shape mirrors backend `DebugCase`.

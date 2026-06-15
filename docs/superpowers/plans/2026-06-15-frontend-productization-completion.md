# Frontend Productization Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `test-driven-development` before production edits. Use `frontend-skill`, `anime-js`, and `gsap-react` for all visual and motion work. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Debug Detection Agent frontend from a functional console to a polished, enterprise-grade, operator-ready product experience with complete information architecture, visual system, motion, accessibility, and workflow validation.

**Architecture:** Keep the existing React/Vite app and API client. Productize by extracting focused UI primitives, then refactor existing workspaces into a coherent console: operations rail, intake, investigation, evidence, report, observability, and writeback. Use GSAP React for scoped lifecycle-safe entrance/layout motion, Anime.js for lightweight stagger/detail motion, and CSS for the primary visual system.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, CSS, GSAP, `@gsap/react`, Anime.js.

---

## Product Direction

**Visual Thesis:** A calm enterprise investigation cockpit with dark evidence-focused hierarchy, translucent operational surfaces, restrained accent color, and precise motion that clarifies state changes.

**Content Plan:**
- Console shell: identify system, current operational state, and primary action.
- Intake: import/sync cases and create jobs without overwhelming the main investigation area.
- Investigation: focus on selected job, evidence, root cause, action status, follow-up lineage, handoff, final attribution, and recovery.
- Operations: show health, worker, budget, writeback, queue, and reopened/recovery risks as scan-first metrics.
- Validation: preserve existing workflows and add product-level regression tests for layout, motion hooks, accessibility, and responsive behavior.

**Interaction Thesis:**
- GSAP handles lifecycle-safe reveal and workspace transitions through scoped refs and cleanup.
- Anime.js handles lightweight staggered flow for repeated panels and trace rows.
- Motion is disabled or reduced for `prefers-reduced-motion`, and no animation may hide active controls from tests or assistive technology.

## Completion Definition

Frontend is considered `100% productized` only when all checklist items below are complete:
- [ ] Existing backend-driven workflows remain functional through the frontend.
- [ ] Console shell, navigation, intake, job queue, evidence, report, observability, and writeback each have production-ready layout and hierarchy.
- [ ] Shared UI primitives exist for buttons, status badges, metrics, surfaces, section headers, timeline rows, and empty/error states.
- [ ] GSAP and Anime.js are used intentionally with cleanup and reduced-motion handling.
- [ ] All existing frontend tests pass and new productization tests cover the redesigned surfaces.
- [ ] Full `.\scripts\verify.ps1`, `git diff --check`, and Ark key scan pass before every commit.
- [ ] A manual preview run verifies the app at `http://localhost:5173/` with backend health at `http://localhost:8000/health`.

## File Map

- `frontend/src/styles/product.css`: Global product visual system, shell layout, primitives, responsive behavior, and motion-safe styles.
- `frontend/src/app/App.tsx`: Console composition and high-level region placement only.
- `frontend/src/app/App.test.tsx`: Product shell, navigation, and high-level workflow regression tests.
- `frontend/src/app/useProductMotion.ts`: Scoped GSAP and Anime.js motion orchestration.
- `frontend/src/ui/ProductPrimitives.tsx`: Shared UI primitives for surface, metric, badge, action row, empty state, and section header.
- `frontend/src/ui/ProductPrimitives.test.tsx`: Primitive rendering and accessibility tests.
- `frontend/src/reports/DebugReportWorkspace.tsx`: Productized investigation workspace composition.
- `frontend/src/reports/DebugReportWorkspace.test.tsx`: Evidence/report workspace tests.
- `frontend/src/reports/ReportPanel.tsx`: Report sections, attribution/recovery lineages, and action controls.
- `frontend/src/reports/ReportPanel.test.tsx`: Report information architecture tests.
- `frontend/src/evidence/EvidenceDetail.tsx`: Evidence preview, artifact links, and evidence metadata layout.
- `frontend/src/evidence/EvidenceDetail.test.tsx`: Evidence visibility and artifact interaction tests.
- `frontend/src/observability/ObservabilitySummaryPanel.tsx`: Operational health dashboard.
- `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`: Observability dashboard metric and action tests.
- `frontend/src/jobs/*.tsx`: Job queue, current job, worker state, and batch job panels.
- `frontend/src/jobs/*.test.tsx`: Job and worker workflow tests.
- `frontend/src/cases/*.tsx`: Case list/detail productization.
- `frontend/src/cases/*.test.tsx`: Case list/detail tests.
- `frontend/src/spreadsheets/*.tsx`: Spreadsheet sync, writeback, audit, and Lark status surfaces.
- `frontend/src/spreadsheets/*.test.tsx`: Spreadsheet and writeback tests.
- `docs/superpowers/plans/2026-06-15-critical-gap-roadmap.md`: High-level roadmap pointer and completed task tracking.

## Execution Policy

Each task must follow:
```powershell
npx --yes pnpm@9.15.4 --dir frontend test -- --run <focused tests>
.\scripts\verify.ps1
git diff --check
git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Commit only after the focused tests and full verification pass.

---

## Implementation Tasks

### Task 46: Product Primitive System

**Files:**
- Create: `frontend/src/ui/ProductPrimitives.tsx`
- Create: `frontend/src/ui/ProductPrimitives.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add tests for shared primitives.
  - Test that `ProductSurface` renders a labelled region.
  - Test that `MetricStrip` renders metric labels and values.
  - Test that `StatusBadge` maps `critical`, `warning`, `success`, and `neutral` to stable class names.
  - Run:
    ```powershell
    npx --yes pnpm@9.15.4 --dir frontend test -- --run src/ui/ProductPrimitives.test.tsx
    ```
  - Expected RED: module `../ui/ProductPrimitives` cannot be resolved.
- [x] Implement `ProductSurface`, `MetricStrip`, `StatusBadge`, `ActionRow`, `EmptyState`, and `SectionHeader`.
  - Use semantic `section`, `header`, and `dl` where appropriate.
  - Keep props minimal and typed.
  - Add CSS classes: `product-surface`, `metric-strip`, `status-badge`, `action-row`, `empty-state`, `section-header`.
- [x] Re-run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/ui/ProductPrimitives.test.tsx
  ```
  - Expected GREEN: all primitive tests pass.
- [x] Run frontend typecheck:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend typecheck
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/ui/ProductPrimitives.tsx frontend/src/ui/ProductPrimitives.test.tsx frontend/src/styles/product.css
  git commit -m "feat: add frontend product primitives"
  ```

### Task 47: Console Navigation And Region Anchors

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests that assert the console has navigation links for `Operations`, `Intake`, `Workspace`, `Observability`, and `Writeback`.
- [x] Add accessible IDs to the main regions:
  - `operations`
  - `case-intake`
  - `investigation-workspace`
  - `observability`
  - `writeback`
- [x] Add a compact top navigation inside the shell hero.
- [x] Add CSS for `agent-shell__nav` and active-like hover/focus states.
- [x] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx -t "console navigation"
  ```
- [x] Run full App tests:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx frontend/src/styles/product.css
  git commit -m "feat: add console navigation anchors"
  ```

### Task 48: Intake And Case Queue Productization

**Files:**
- Modify: `frontend/src/imports/ImportWorkspace.tsx`
- Modify: `frontend/src/imports/ImportWorkspace.test.tsx`
- Modify: `frontend/src/cases/ImportedCasesPanel.tsx`
- Modify: `frontend/src/cases/ImportedCasesPanel.test.tsx`
- Modify: `frontend/src/cases/ImportedCaseListPanel.tsx`
- Modify: `frontend/src/cases/ImportedCaseListPanel.test.tsx`
- Modify: `frontend/src/cases/ImportedCaseDetailPanel.tsx`
- Modify: `frontend/src/cases/ImportedCaseDetailPanel.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests requiring intake panels to expose clear headings, helper copy, and consistent empty states.
- [x] Replace plain stacked import panels with product surfaces using `ProductSurface`, `SectionHeader`, and `EmptyState`.
- [x] Add case queue density improvements: case count, filtered count, region count, and primary action row.
- [x] Add CSS for `intake-stack`, `case-queue`, `case-detail`, and `import-panel`.
- [x] Run focused tests:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/imports/ImportWorkspace.test.tsx src/cases/ImportedCasesPanel.test.tsx src/cases/ImportedCaseListPanel.test.tsx src/cases/ImportedCaseDetailPanel.test.tsx
  ```
- [ ] Commit:
  ```powershell
  git add frontend/src/imports frontend/src/cases frontend/src/styles/product.css
  git commit -m "feat: productize case intake workspace"
  ```

### Task 49: Job Queue And Worker Operations Productization

**Files:**
- Modify: `frontend/src/jobs/WorkerControlsPanel.tsx`
- Modify: `frontend/src/jobs/WorkerControlsPanel.test.tsx`
- Modify: `frontend/src/jobs/WorkerStatusPanel.tsx`
- Modify: `frontend/src/jobs/WorkerStatusPanel.test.tsx`
- Modify: `frontend/src/jobs/BatchJobsPanel.tsx`
- Modify: `frontend/src/jobs/BatchJobsPanel.test.tsx`
- Modify: `frontend/src/jobs/BatchJobListPanel.tsx`
- Modify: `frontend/src/jobs/BatchJobListPanel.test.tsx`
- Modify: `frontend/src/jobs/CurrentJobPanel.tsx`
- Modify: `frontend/src/jobs/CurrentJobPanel.test.tsx`
- Modify: `frontend/src/jobs/JobStatusPanel.tsx`
- Modify: `frontend/src/jobs/JobStatusPanel.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests for worker health status badges and queue summary metrics.
- [x] Use `StatusBadge` for job status, retry severity, worker running state, and failed job state.
- [x] Add queue metric strip: total, completed, failed, pending, unloaded.
- [x] Productize current job panel with a persistent action row for load report and evidence.
- [x] Run focused tests:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/jobs/WorkerControlsPanel.test.tsx src/jobs/WorkerStatusPanel.test.tsx src/jobs/BatchJobsPanel.test.tsx src/jobs/BatchJobListPanel.test.tsx src/jobs/CurrentJobPanel.test.tsx src/jobs/JobStatusPanel.test.tsx
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/jobs frontend/src/styles/product.css
  git commit -m "feat: productize job operations"
  ```

### Task 50: Observability Dashboard Productization

**Files:**
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests requiring grouped observability sections:
  - Job queue
  - Worker runtime
  - Evidence quality
  - Usage budget
  - Strategy and targeted feedback
  - Attribution verification and recovery
  - Health actions
- [x] Convert flat paragraphs into metric strips and status sections.
- [x] Use `StatusBadge` for health level and budget status.
- [x] Preserve existing text assertions or update tests to assert both old values and new grouped labels.
- [x] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/observability/ObservabilitySummaryPanel.test.tsx
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/observability frontend/src/styles/product.css
  git commit -m "feat: productize observability dashboard"
  ```

### Task 51: Evidence Workspace Productization

**Files:**
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Modify: `frontend/src/evidence/EvidenceDetail.test.tsx`
- Modify: `frontend/src/experiments/ExperimentTimeline.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests requiring evidence preview to show request metadata, judge score, reasons, artifacts, and selected evidence state in separate regions.
- [x] Productize `EvidenceDetail` into evidence summary, model output, judge result, artifacts, and media links.
- [x] Productize `ExperimentTimeline` with timeline row classes and selected evidence affordances.
- [x] Add Anime.js `data-anime-flow` to timeline rows only when useful.
- [x] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx src/reports/DebugReportWorkspace.test.tsx
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/evidence frontend/src/experiments frontend/src/reports/DebugReportWorkspace.test.tsx frontend/src/styles/product.css
  git commit -m "feat: productize evidence workspace"
  ```

### Task 52: Report And Root-Cause Workspace Productization

**Files:**
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.test.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Modify: `frontend/src/reports/ReportPanel.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [x] Add RED tests for report workspace regions:
  - Root cause
  - Evidence spine
  - Evaluation diagnostics
  - Recommended actions
  - Follow-up experiments
  - Strategy history
  - Targeted probe history
  - Human handoff
  - Final attribution
  - Recovery and reinvestigation
- [x] Replace dense paragraph stacks with section headers, metric strips, lineage rows, and action rows.
- [x] Preserve all existing buttons and callbacks.
- [x] Add stable classes: `report-workspace`, `root-cause-panel`, `lineage-row`, `evidence-spine`, `action-console`.
- [x] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/reports/DebugReportWorkspace.test.tsx src/reports/ReportPanel.test.tsx
  ```
- [x] Commit:
  ```powershell
  git add frontend/src/reports frontend/src/styles/product.css
  git commit -m "feat: productize debug report workspace"
  ```

### Task 53: Spreadsheet And Writeback Operations Productization

**Files:**
- Modify: `frontend/src/spreadsheets/SpreadsheetSyncPanel.tsx`
- Modify: `frontend/src/spreadsheets/SpreadsheetSyncPanel.test.tsx`
- Modify: `frontend/src/spreadsheets/SpreadsheetWritebackPanel.tsx`
- Modify: `frontend/src/spreadsheets/SpreadsheetWritebackPanel.test.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditSummary.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditSummary.test.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditList.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditList.test.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditRow.tsx`
- Modify: `frontend/src/spreadsheets/WritebackAuditRow.test.tsx`
- Modify: `frontend/src/spreadsheets/LarkSpreadsheetStatusPanel.tsx`
- Modify: `frontend/src/spreadsheets/LarkSpreadsheetStatusPanel.test.tsx`
- Modify: `frontend/src/styles/product.css`

- [ ] Add RED tests for sync status, writeback audit health, retry affordances, and Lark connection state.
- [ ] Productize spreadsheet controls using surfaces, status badges, audit rows, and action rows.
- [ ] Ensure failed/skipped/succeeded audit filters remain accessible.
- [ ] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/spreadsheets/SpreadsheetSyncPanel.test.tsx src/spreadsheets/SpreadsheetWritebackPanel.test.tsx src/spreadsheets/WritebackAuditSummary.test.tsx src/spreadsheets/WritebackAuditList.test.tsx src/spreadsheets/WritebackAuditRow.test.tsx src/spreadsheets/LarkSpreadsheetStatusPanel.test.tsx
  ```
- [ ] Commit:
  ```powershell
  git add frontend/src/spreadsheets frontend/src/styles/product.css
  git commit -m "feat: productize spreadsheet operations"
  ```

### Task 54: Motion System Hardening

**Files:**
- Modify: `frontend/src/app/useProductMotion.ts`
- Create: `frontend/src/app/useProductMotion.test.tsx`
- Modify: `frontend/src/styles/product.css`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] Add RED tests for reduced motion:
  - Mock `window.matchMedia("(prefers-reduced-motion: reduce)")`.
  - Assert app still renders shell and controls.
  - Assert motion hook does not hide primary controls.
- [ ] Add tests proving motion selectors are scoped to `data-motion-scope="debug-console"`.
- [ ] Harden `useProductMotion` so animations never set `visibility:hidden` or disable pointer access.
- [ ] Add CSS motion tokens and reduce-motion overrides for transitions.
- [ ] Run:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/useProductMotion.test.tsx src/app/App.test.tsx
  ```
- [ ] Commit:
  ```powershell
  git add frontend/src/app/useProductMotion.ts frontend/src/app/useProductMotion.test.tsx frontend/src/app/App.test.tsx frontend/src/styles/product.css
  git commit -m "feat: harden frontend motion system"
  ```

### Task 55: Responsive And Accessibility Completion

**Files:**
- Modify: `frontend/src/styles/product.css`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: component tests that need accessible label updates.

- [ ] Add RED tests for accessible region labels and landmark structure.
- [ ] Add keyboard focus styles for links, buttons, inputs, and action rows.
- [ ] Add responsive breakpoints for desktop, tablet, and mobile.
- [ ] Ensure all critical controls remain visible and reachable in the DOM without relying on hover.
- [ ] Run complete frontend tests:
  ```powershell
  npx --yes pnpm@9.15.4 --dir frontend test -- --run
  ```
- [ ] Commit:
  ```powershell
  git add frontend/src frontend/package.json frontend/pnpm-lock.yaml
  git commit -m "feat: complete frontend accessibility and responsive polish"
  ```

### Task 56: Frontend Preview Dogfood And Fix Pass

**Files:**
- Modify: `frontend/src/**`
- Modify: `docs/superpowers/plans/2026-06-15-frontend-productization-completion.md`

- [ ] Start services:
  ```powershell
  $env:PYTHONPATH='src'; python -m uvicorn debug_agent.main:app --host 127.0.0.1 --port 8000 --reload
  npx --yes pnpm@9.15.4 --dir frontend dev -- --host 127.0.0.1 --port 5173
  ```
- [ ] Verify:
  ```powershell
  Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
  Invoke-WebRequest -UseBasicParsing http://localhost:5173/
  ```
- [ ] Dogfood manually through:
  - Load observability summary.
  - Submit debug job.
  - Load persisted report.
  - Open evidence.
  - Run report follow-up controls where fixture data allows.
  - Load spreadsheet controls and writeback audit surfaces.
- [ ] Fix any visual, accessibility, or interaction issues discovered.
- [ ] Re-run:
  ```powershell
  .\scripts\verify.ps1
  git diff --check
  git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
  ```
- [ ] Commit:
  ```powershell
  git add frontend/src docs/superpowers/plans/2026-06-15-frontend-productization-completion.md
  git commit -m "fix: polish frontend dogfood findings"
  ```

### Task 57: Final Frontend Productization Report

**Files:**
- Modify: `docs/superpowers/plans/2026-06-15-frontend-productization-completion.md`
- Modify: `docs/superpowers/plans/2026-06-15-critical-gap-roadmap.md`

- [ ] Mark all frontend productization tasks complete.
- [ ] Add a final status section with:
  - Frontend completion percentage: `100%`
  - Verification command outputs
  - Manual dogfood summary
  - Known remaining backend-only items
- [ ] Run final verification:
  ```powershell
  .\scripts\verify.ps1
  git diff --check
  git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
  ```
- [ ] Commit:
  ```powershell
  git add docs/superpowers/plans/2026-06-15-frontend-productization-completion.md docs/superpowers/plans/2026-06-15-critical-gap-roadmap.md
  git commit -m "docs: complete frontend productization plan"
  ```

## Progress Gates

- Gate A, after Task 49: core shell, intake, jobs, and worker surfaces are productized.
- Gate B, after Task 52: evidence and report workspace are productized.
- Gate C, after Task 54: motion is hardened and accessible.
- Gate D, after Task 56: manual dogfood is complete.
- Gate E, after Task 57: frontend productization is marked `100%`.

## Self-Review

- Spec coverage: The plan covers the full frontend, including shell, intake, jobs, evidence, report, observability, spreadsheets, motion, accessibility, responsive behavior, and dogfood.
- Placeholder scan: No task uses `TBD`, `TODO`, or unspecified future implementation.
- Type consistency: Shared primitives are introduced first and reused by later tasks; motion remains scoped through `useProductMotion`; all tests reference existing file paths or files created by earlier tasks.

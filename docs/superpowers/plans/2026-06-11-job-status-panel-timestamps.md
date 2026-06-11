# Job Status Panel Timestamps Implementation Plan

> **For agentic workers:** Use TDD. Job detail views should show the same audit timestamps as list views.

**Goal:** Make opened job details auditable by displaying creation and update times.

**Architecture:** Add a focused `JobStatusPanel` test and render formatted timestamps with raw ISO values preserved in `title` attributes.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Detail Timestamp Display

**Files:**
- Modify: `frontend/src/jobs/JobStatusPanel.tsx`
- Test: `frontend/src/jobs/JobStatusPanel.test.tsx`

- [x] **Step 1: Add failing component test**

Assert `JobStatusPanel` renders formatted created/updated timestamps and preserves raw ISO values in `title`.

- [x] **Step 2: Run focused component test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/jobs/JobStatusPanel.test.tsx`
Expected: FAIL because timestamps are not rendered.

- [x] **Step 3: Implement timestamp rendering**

Render formatted created/updated timestamps when present.

- [x] **Step 4: Run focused component test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/jobs/JobStatusPanel.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(jobs): show timestamps in job detail`.

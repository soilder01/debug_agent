# Frontend Writeback Audit List Component

## Goal

Extract writeback audit list rendering from `App.tsx` into a focused component.

## Scope

- Add `WritebackAuditList` for total count, active filter, audit rows, retry results, and pagination action.
- Reuse `WritebackAuditRow` for each audit.
- Preserve existing open job, retry, load more, and writeback result field behavior.
- Keep `App.tsx` responsible for data fetching and state only.

## TDD Steps

1. RED: Add component tests for list rendering and load-more behavior.
2. GREEN: Implement `WritebackAuditList` and wire `App.tsx` to use it.
3. VERIFY: Run focused component/App tests, full verification, diagnostics, whitespace check, and secret scan.

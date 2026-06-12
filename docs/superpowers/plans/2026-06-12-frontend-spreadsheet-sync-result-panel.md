# Frontend Spreadsheet Sync Result Panel

## Goal

Extract spreadsheet sync result rendering from `App.tsx` into a focused component to keep the main app as orchestration code.

## Steps

1. Add a failing component test for imported case count, imported row summary, and rejected row summary.
2. Implement `SpreadsheetSyncResultPanel`.
3. Replace inline sync result JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing user-facing sync result text remains unchanged.
- Empty imported/rejected row lists render as `无`.
- Component tests cover both populated and empty summaries.

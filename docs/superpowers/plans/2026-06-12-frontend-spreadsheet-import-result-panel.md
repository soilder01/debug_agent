# Frontend Spreadsheet Import Result Panel

## Goal

Extract spreadsheet rows import result rendering from `App.tsx` into a component that mirrors the sync result panel.

## Steps

1. Add a failing component test for imported case count, imported rows, and rejected rows.
2. Implement `SpreadsheetImportResultPanel`.
3. Replace inline import result JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing spreadsheet import result text remains unchanged.
- Empty imported/rejected lists render as `无`.
- App integration tests continue to pass.

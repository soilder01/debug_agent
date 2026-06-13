# Frontend Spreadsheet Writeback Panel

## Goal

Extract current job spreadsheet writeback controls and result/audit detail rendering from `App.tsx`.

## Steps

1. Add a failing component test for writeback actions, writeback result fields, audit detail, and audit error rendering.
2. Implement `SpreadsheetWritebackPanel`.
3. Replace inline spreadsheet writeback JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing button labels and writeback/audit text remain unchanged.
- Writeback audit errors render with `role="alert"`.
- App integration tests continue to pass.

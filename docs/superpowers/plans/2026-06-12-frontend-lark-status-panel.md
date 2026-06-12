# Frontend Lark Status Panel

## Goal

Extract Lark spreadsheet status rendering from `App.tsx` into a reusable component so spreadsheet connectivity, timeout, and error state UI can evolve independently.

## Steps

1. Add a failing component test for configured status, connectivity state, spreadsheet reference, timeout, and error message.
2. Implement `LarkSpreadsheetStatusPanel`.
3. Replace the inline Lark status JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Configured/unconfigured states render with existing user-facing text.
- Connectivity status, spreadsheet/sheet IDs, CLI timeout, and optional error message remain visible.
- Existing `App` integration tests continue to pass.

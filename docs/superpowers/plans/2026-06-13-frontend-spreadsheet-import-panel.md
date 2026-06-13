# Frontend Spreadsheet Import Panel

## Goal

Extract spreadsheet rows JSON import controls and result rendering from `App.tsx`.

## Steps

1. Add a failing component test for textarea value changes, import action, and result rendering.
2. Implement `SpreadsheetImportPanel` using `SpreadsheetImportResultPanel`.
3. Replace inline spreadsheet rows import JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing spreadsheet rows JSON label and button text remain unchanged.
- Textarea changes delegate the full JSON string.
- Existing spreadsheet import result rendering remains unchanged.

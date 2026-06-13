# Frontend CSV Import Panel

## Goal

Extract CSV import controls and result rendering from `App.tsx`.

## Steps

1. Add a failing component test for textarea value changes, import action, and result rendering.
2. Implement `CSVImportPanel` using `CSVImportResultPanel`.
3. Replace inline CSV import JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing CSV label and button text remain unchanged.
- Textarea changes delegate the full CSV text.
- Existing CSV import result rendering remains unchanged.

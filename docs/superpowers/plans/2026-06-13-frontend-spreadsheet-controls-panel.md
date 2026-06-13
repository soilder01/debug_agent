# Frontend Spreadsheet Controls Panel

## Goal

Extract spreadsheet sync controls from `App.tsx` into a focused component.

## Steps

1. Add a failing component test for URL/id inputs and all spreadsheet sync/audit action buttons.
2. Implement `SpreadsheetControlsPanel`.
3. Replace inline spreadsheet control JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing labels and button names remain unchanged.
- Input changes delegate new values to `App`.
- Status/audit actions delegate the same filter values as before.

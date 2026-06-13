# Frontend Imported Cases Panel

## Goal

Extract the imported cases section wrapper from `App.tsx` into a focused component.

## Steps

1. Add a failing component test for the section heading, initial load action, list rendering, and selected detail rendering.
2. Implement `ImportedCasesPanel` using `ImportedCaseListPanel` and `ImportedCaseDetailPanel`.
3. Replace inline Imported Cases section JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing heading and button names remain unchanged.
- List and detail panels remain hidden until imported cases exist.
- All callbacks delegate unchanged values to `App`.

# Frontend Imported Case Detail Panel

## Goal

Extract selected imported case detail rendering from `App.tsx` into a focused component.

## Steps

1. Add a failing component test for selected case metadata, golden answers, regions, predictions, human notes, and submit action.
2. Implement `ImportedCaseDetailPanel`.
3. Replace inline selected case detail JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing selected case detail text remains unchanged.
- Missing region labels, human status, and human root cause fall back to existing defaults.
- Submit debug job action delegates the selected case id.

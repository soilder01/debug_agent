# Frontend Imported Case List Panel

## Goal

Extract imported case list rendering and list-level actions from `App.tsx` into a focused component.

## Steps

1. Add a failing component test for list counts, filters, pagination button, batch-fill action, and case detail action.
2. Implement `ImportedCaseListPanel`.
3. Replace the inline imported case list JSX in `App.tsx` while leaving selected case detail rendering in place.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing imported case list text and buttons remain unchanged.
- `Load more imported cases` appears only when unloaded cases remain.
- Row-level case detail action delegates the selected case id.

# Frontend Batch Job List Panel

## Goal

Extract batch job summary and list rendering from `App.tsx` into a focused component.

## Steps

1. Add a failing component test for summary counts, progress, rejected cases, timestamps, retry recommendation details, job opening, evidence opening, and pagination.
2. Implement `BatchJobListPanel`.
3. Replace inline batch job result JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing batch job text and button labels remain unchanged.
- `Load more debug jobs` appears only when unloaded jobs remain.
- Job and evidence actions delegate ids without changing App orchestration.

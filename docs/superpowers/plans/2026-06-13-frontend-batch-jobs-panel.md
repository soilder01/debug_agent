# Frontend Batch Jobs Panel

## Goal

Extract the Batch Jobs section wrapper from `App.tsx`.

## Steps

1. Add a failing component test for controls rendering and optional batch list rendering.
2. Implement `BatchJobsPanel` using `BatchJobControlsPanel` and `BatchJobListPanel`.
3. Replace inline Batch Jobs section JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing controls and list text remain unchanged.
- Batch list stays hidden until a batch result exists.
- All callbacks delegate unchanged values to `App`.

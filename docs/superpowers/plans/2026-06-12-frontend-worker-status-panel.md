# Frontend Worker Status Panel

## Goal

Extract worker runtime status rendering from `App.tsx` into a focused component for future observability expansion.

## Steps

1. Add a failing component test for worker counters, writeback settings, report base URL, and error rendering.
2. Implement `WorkerStatusPanel`.
3. Replace inline worker status JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing worker status text remains unchanged.
- Worker error is rendered with `role="alert"` when present.
- App integration tests continue to pass.

# Frontend Worker Controls Panel

## Goal

Extract worker start/stop controls and status rendering from `App.tsx`.

## Steps

1. Add a failing component test for Start/Stop worker actions and status rendering.
2. Implement `WorkerControlsPanel` using `WorkerStatusPanel`.
3. Replace inline Worker section JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing Worker section heading and button names remain unchanged.
- Start/Stop actions delegate to `App`.
- Worker status remains hidden until status exists.

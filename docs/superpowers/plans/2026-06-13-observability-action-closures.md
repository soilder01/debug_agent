# Observability Action Closures

## Goal

Turn observability recommended actions into direct operator actions so users can move from risk detection to mitigation without hunting through the UI.

## Scope

- Add optional action callbacks to `ObservabilitySummaryPanel`.
- Provide buttons for failed jobs, failed writeback audits, and worker backlog draining.
- Wire those buttons in `App` to existing load/start functions.
- Keep the slice frontend-only because the backend already returns health reasons and actions.

## Verification

- RED: component/App tests fail because action buttons are missing.
- GREEN: focused tests pass.
- Full: run `verify.ps1`, diagnostics, whitespace check, and secret scan before commit.

# Observability Budget Status

## Goal

Add a configurable usage budget status to observability so long-running agent runs can surface budget risk before hard budget enforcement is added.

## Scope

- Read `DEBUG_AGENT_USAGE_BUDGET_UNITS` from environment.
- Include budget status, configured budget, and utilization in `/observability/summary`.
- Mark observability health critical when estimated usage exceeds the configured budget.
- Render budget status in the frontend observability panel.

## Verification

- RED: settings, backend API, and frontend tests fail because budget status is missing.
- GREEN: focused tests pass.
- Full: run `verify.ps1`, diagnostics, whitespace check, and secret scan before commit.

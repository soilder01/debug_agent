# Budget Enforcement

## Goal

Add an opt-in hard budget gate so new debug jobs are blocked when observed usage is already over the configured budget.

## Scope

- Read `DEBUG_AGENT_ENFORCE_USAGE_BUDGET` from environment.
- Keep enforcement disabled by default.
- Reject single-case debug job submission with HTTP 429 when enforcement is enabled and usage is over budget.
- Keep existing observability budget status unchanged.

## Verification

- RED: settings/API tests fail because enforcement is missing.
- GREEN: focused tests pass.
- Full: run `verify.ps1`, diagnostics, whitespace check, and secret scan before commit.

# Frontend Writeback Audit Active Filter

## Goal

Show the currently loaded writeback audit filter so operators can distinguish all, succeeded, failed, and skipped audit lists.

## Scope

- Render an active filter label above the audit list.
- Use `all` when audits are loaded without a status filter.
- Preserve existing filter buttons, summary drilldown, pagination, retry, job, and report actions.

## TDD Steps

1. RED: Add frontend tests for active filter labels for all and failed audit lists.
2. GREEN: Render the active filter label from existing audit filter state.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

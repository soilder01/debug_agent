# Frontend Hide Succeeded Writeback Retry

## Goal

Prevent accidental writeback retries for audits that already succeeded.

## Scope

- Hide the row-level `Retry writeback` action for succeeded audits.
- Keep retry available for failed and skipped audits.
- Preserve open job, report link, filters, pagination, and retry result behavior.

## TDD Steps

1. RED: Add a frontend test proving succeeded audit rows do not show retry.
2. GREEN: Conditionally render retry only for non-succeeded audits.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

# Frontend Writeback Retry Eligibility

## Goal

Make writeback retry availability explicit in each audit row so operators understand why only failed audits can be retried directly.

## Scope

- Show `Retry eligibility：available` for failed audits.
- Show `Retry eligibility：unavailable` for succeeded and skipped audits.
- Preserve existing retry visibility rules and audit actions.

## TDD Steps

1. RED: Add frontend tests for retry eligibility labels on failed and skipped audit rows.
2. GREEN: Render the eligibility label from audit status.
3. VERIFY: Run focused frontend tests, full verification, diagnostics, whitespace check, and secret scan.

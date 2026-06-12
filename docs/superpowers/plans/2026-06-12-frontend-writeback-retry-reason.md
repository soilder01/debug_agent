# Frontend Writeback Retry Reason

## Goal

Explain why a writeback audit row can or cannot be retried directly.

## Scope

- Show `Retry reason：last writeback failed` for failed audits.
- Show `Retry reason：already succeeded` for succeeded audits.
- Show `Retry reason：missing prerequisites` for skipped audits.
- Preserve existing retry eligibility, filters, pagination, job, retry, and report actions.

## TDD Steps

1. RED: Add frontend tests for retry reason labels on failed, succeeded, and skipped audit rows.
2. GREEN: Render retry reason from audit status.
3. VERIFY: Run focused frontend tests, full verification, diagnostics, whitespace check, and secret scan.

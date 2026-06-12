# Frontend Writeback Audit Policy

## Goal

Make writeback audit retry eligibility and reason rules explicit, testable, and reusable outside the row component.

## Steps

1. Add a focused failing component test that requires failed writebacks to surface the original error in the retry reason.
2. Implement the minimal behavior in the current row component.
3. Extract retry eligibility/reason logic into a small policy module with pure function tests.
4. Re-run focused frontend tests, full verification, diagnostics, secret scan, and checkpoint commit.

## Acceptance

- Failed audits remain the only retryable status.
- Failed audits with an error show the error detail in the retry reason.
- Succeeded/skipped/non-failed audits remain non-retryable.
- Policy rules are covered by direct unit tests and component tests.

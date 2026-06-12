# Writeback Audit Newest First

## Goal

Make spreadsheet writeback audit pagination deterministic and operator-friendly by listing newest audit updates first.

## Scope

- Sort writeback audits by `updated_at` descending.
- Keep `job_id` as a stable tie-breaker.
- Update pagination expectations to match newest-first ordering.

## TDD Steps

1. RED: Add a repository test showing an updated audit appears before older audits.
2. GREEN: Change repository audit list ordering to newest first.
3. VERIFY: Run focused backend test, full verification, diagnostics, whitespace check, and secret scan.

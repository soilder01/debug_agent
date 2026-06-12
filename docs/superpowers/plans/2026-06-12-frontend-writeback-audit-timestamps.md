# Frontend Writeback Audit Timestamps

## Goal

Show writeback audit update timestamps in the operator audit list so newest-first ordering is visible and actionable.

## Scope

- Render `updated_at` for each spreadsheet writeback audit row.
- Keep existing job, retry, report-link, filter, and pagination actions unchanged.
- Avoid changing backend audit APIs.

## TDD Steps

1. RED: Add a frontend test that expects an audit row to show its update timestamp.
2. GREEN: Render `updated_at` in the audit row text.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

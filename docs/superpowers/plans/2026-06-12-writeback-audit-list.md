# Writeback Audit List

## Goal

Allow operators to drill into spreadsheet writeback audit records by status, with pagination, after seeing global summary counts.

## Scope

- Add repository listing and counting methods for writeback audits.
- Add a backend API endpoint to list audits with optional `status`, `limit`, and `offset`.
- Reuse detailed audit fields without loading unrelated job data.

## TDD Steps

1. RED: Add repository tests for status-filtered audit listing and counting.
2. GREEN: Implement repository methods.
3. RED: Add API tests for filtered audit listing.
4. GREEN: Implement list endpoint and response model.
5. VERIFY: Run focused tests, full verification, diagnostics, whitespace check, and secret scan.


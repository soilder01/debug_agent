# Writeback Audit Summary

## Goal

Expose lightweight spreadsheet writeback audit counts so operators can quickly see succeeded, failed, and skipped writeback outcomes.

## Scope

- Add repository aggregation by writeback audit status.
- Add an API endpoint for writeback audit summaries.
- Keep detailed per-job audit endpoint unchanged.

## TDD Steps

1. RED: Add repository and API tests for status counts.
2. GREEN: Implement aggregation and endpoint.
3. VERIFY: Run focused tests, full verification, diagnostics, whitespace check, and secret scan.


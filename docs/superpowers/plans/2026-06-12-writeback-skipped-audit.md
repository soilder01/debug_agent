# Writeback Skipped Audit

## Goal

Persist skipped automatic writeback outcomes so completed jobs explain why no spreadsheet row was updated.

## Scope

- Record `skipped` when a completion hook cannot rebuild a report.
- Record `skipped` when a report exists but no spreadsheet row mapping exists.
- Keep skipped outcomes non-fatal for the worker.
- Preserve existing success and failure audit behavior.

## TDD Steps

1. RED: Add tests for skipped audit records on missing report and missing mapping.
2. GREEN: Save skipped audit records in the completion hook.
3. VERIFY: Run focused tests, full verification, diagnostics, whitespace check, and secret scan.


# Frontend Open Report From Writeback Audit

## Goal

Let operators open the persisted analysis report URL directly from each spreadsheet writeback audit row.

## Scope

- Render a report link for audit rows that include `report_url`.
- Keep rows without a report URL unchanged.
- Preserve existing open-job, retry, refresh, and pagination behavior.

## TDD Steps

1. RED: Add a frontend test for the audit row report link.
2. GREEN: Render the report link only when `report_url` is present.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

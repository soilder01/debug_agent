# Frontend Writeback Audit Pagination

## Goal

Allow operators to load additional spreadsheet writeback audit pages from the frontend when the audit list has more records than the first page.

## Scope

- Track the active writeback audit status filter.
- Append additional audit pages using the current audit count as `offset`.
- Show a load-more action only when more audits are available.
- Preserve failed/skipped first-page loading.

## TDD Steps

1. RED: Add a frontend test for loading more failed writeback audits.
2. GREEN: Track active status and append next-page audit results.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.


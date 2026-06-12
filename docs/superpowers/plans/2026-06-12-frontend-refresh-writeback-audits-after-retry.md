# Frontend Refresh Writeback Audits After Retry

## Goal

Keep writeback audit list and summary counts current after an operator retries a spreadsheet writeback.

## Scope

- After a successful audit-row retry, reload the active audit status page.
- Reload writeback audit summary counts after the retry.
- Preserve the existing retry result display.
- Keep failures visible through the existing global error alert.

## TDD Steps

1. RED: Add a frontend test showing retry refreshes the active failed audit list and summary.
2. GREEN: Refresh the active audit list and summary after successful retry.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

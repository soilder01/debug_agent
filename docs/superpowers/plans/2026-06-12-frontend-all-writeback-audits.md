# Frontend All Writeback Audits

## Goal

Let operators inspect the full spreadsheet writeback audit ledger, not only failed or skipped rows.

## Scope

- Add a `Load all writeback audits` action.
- Fetch audits without a status filter.
- Preserve existing failed/skipped filtering.
- Allow pagination for the all-audits view.

## TDD Steps

1. RED: Add a frontend test for loading all writeback audits without a status query.
2. GREEN: Add the all-audits action and support pagination without a status filter.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

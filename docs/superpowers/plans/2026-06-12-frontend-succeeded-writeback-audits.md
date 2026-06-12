# Frontend Succeeded Writeback Audits

## Goal

Let operators open succeeded spreadsheet writeback audits from the main spreadsheet operations area, not only from summary drilldown.

## Scope

- Add a top-level `Load succeeded writeback audits` action.
- Reuse the existing audit list loader with `status=succeeded`.
- Preserve all, failed, skipped, summary drilldown, pagination, retry, job, and report actions.

## TDD Steps

1. RED: Add a frontend test that expects the succeeded audit filter button to call the succeeded audit list API.
2. GREEN: Add the top-level succeeded audit filter button.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

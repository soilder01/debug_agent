# Frontend Writeback Audit Field Count

## Goal

Show how many spreadsheet fields were persisted in each writeback audit row.

## Scope

- Render `Writeback audit fields：N` for every audit row.
- Keep the existing per-field rendering when fields are present.
- Preserve filters, pagination, retry eligibility, retry reasons, job, retry, and report actions.

## TDD Steps

1. RED: Add a frontend test that expects a succeeded audit row to show its field count.
2. GREEN: Render the field count from `Object.keys(audit.fields).length`.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

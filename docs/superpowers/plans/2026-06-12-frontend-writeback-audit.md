# Frontend Writeback Audit

## Goal

Let operators inspect the latest spreadsheet writeback audit from the web UI for a selected job.

## Scope

- Add a frontend API client type and fetch helper.
- Add state and action in the main app.
- Render status, row, report URL, error message, and updated time.
- Keep manual writeback result rendering intact.

## TDD Steps

1. RED: Extend the report/writeback UI test to load and render writeback audit status.
2. GREEN: Add client helper and UI rendering.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.


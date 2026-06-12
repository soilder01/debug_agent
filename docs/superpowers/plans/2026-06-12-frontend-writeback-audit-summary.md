# Frontend Writeback Audit Summary

## Goal

Show global spreadsheet writeback audit counts in the frontend so operators can quickly inspect succeeded, failed, and skipped writeback outcomes.

## Scope

- Add a frontend API client helper for `GET /spreadsheets/writeback/audits/summary`.
- Add state and action in the main app.
- Render total, succeeded, failed, and skipped counts in the spreadsheet operations area.

## TDD Steps

1. RED: Add a frontend test for loading and rendering writeback audit summary counts.
2. GREEN: Add TypeScript types, client helper, state, button, and rendering.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.


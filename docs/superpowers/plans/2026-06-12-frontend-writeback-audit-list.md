# Frontend Writeback Audit List

## Goal

Let operators drill into spreadsheet writeback audits from the frontend after seeing summary counts.

## Scope

- Add frontend API client support for `GET /spreadsheets/writeback/audits`.
- Add UI actions to load failed and skipped audits.
- Render audit job id, status, row, error, and total count.
- Keep detailed per-job audit view unchanged.

## TDD Steps

1. RED: Add a frontend test for loading failed writeback audits.
2. GREEN: Add types, client helper, state, buttons, and rendering.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.


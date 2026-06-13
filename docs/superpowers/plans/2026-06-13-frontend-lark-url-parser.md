# Frontend Lark URL Parser

## Goal

Move Lark spreadsheet URL parsing out of `App.tsx` into a reusable, directly tested utility.

## Steps

1. Add a failing pure function test for valid Lark sheet URLs and validation errors.
2. Implement `parseLarkSpreadsheetUrl` in a spreadsheet utility module.
3. Replace the inline parser in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Valid URLs return `spreadsheetId` and `sheetId`.
- Missing `/sheets/{spreadsheet_id}` and missing `sheet` query keep existing error messages.
- App integration tests continue to pass.

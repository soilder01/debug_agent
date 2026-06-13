# Frontend Spreadsheet Sync Panel

## Goal

Extract the spreadsheet sync workspace from `App.tsx` into a focused `SpreadsheetSyncPanel` component while keeping API orchestration and state ownership in `App`.

## Scope

- Compose existing spreadsheet controls, Lark status, sync result, writeback audit summary, and audit list components.
- Preserve existing user-visible labels and actions.
- Add a focused component test before implementation.
- Keep `App.test.tsx` as the integration safety net.

## Verification

- RED: `SpreadsheetSyncPanel.test.tsx` fails because the component is missing.
- GREEN: focused spreadsheet panel test passes.
- Regression: focused `App.test.tsx` still passes.
- Full: run repository verification, diagnostics, whitespace check, and secret scan before commit.

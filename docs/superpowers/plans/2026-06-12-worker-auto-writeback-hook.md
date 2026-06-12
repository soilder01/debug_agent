# Worker Auto Writeback Hook

## Goal

Automatically write completed job reports back to mapped Lark spreadsheet rows through a reusable worker completion hook.

## Scope

- Add a focused completion hook factory in `debug_agent.spreadsheets.writeback`.
- Rebuild the persisted job report with `build_report_for_job`.
- Resolve the persisted spreadsheet row mapping with existing writeback helpers.
- Generate a stable report URL from a configured base URL.
- Skip safely when a report or mapping is unavailable.

## TDD Steps

1. RED: Add a test proving a completed job writes generated report fields to the mapped row.
2. GREEN: Implement the minimal hook factory.
3. RED: Add a test proving missing reports are skipped without calling the spreadsheet client.
4. GREEN: Keep the hook safe for incomplete persistence state.
5. VERIFY: Run focused backend tests, full verification, diagnostics, whitespace check, and secret scan.


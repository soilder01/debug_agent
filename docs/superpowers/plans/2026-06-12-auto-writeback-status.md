# Auto Writeback Status

## Goal

Expose automatic spreadsheet writeback status in the API and frontend Worker panel so operators can verify whether completed jobs will update Lark rows automatically.

## Scope

- Extend worker status with completion hook visibility.
- Return the configured report base URL from worker API status responses.
- Render automatic writeback state in the frontend Worker panel.
- Preserve existing worker lifecycle behavior.

## TDD Steps

1. RED: Update backend worker status expectations for auto-writeback visibility.
2. GREEN: Add completion hook metadata and API status response fields.
3. RED: Add frontend Worker panel expectation for auto-writeback status.
4. GREEN: Render the new fields.
5. VERIFY: Run focused backend/frontend tests, full verification, diagnostics, whitespace check, and secret scan.


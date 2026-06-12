# Frontend Retry Writeback Audit

## Goal

Let operators retry a failed or skipped spreadsheet writeback directly from the writeback audit list.

## Scope

- Add a row-level `Retry writeback` action in the audit list.
- Reuse the existing job writeback API and audit row `report_url`.
- Render the retry result with the existing spreadsheet writeback result panel.
- Preserve audit list drilldown and pagination behavior.

## TDD Steps

1. RED: Add a frontend test for retrying writeback from an audit row.
2. GREEN: Add the retry action and call the existing writeback client helper.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

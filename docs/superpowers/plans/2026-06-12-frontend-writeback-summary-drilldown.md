# Frontend Writeback Summary Drilldown

## Goal

Let operators jump from writeback audit summary counts directly into the matching audit list.

## Scope

- Add summary-level drilldown actions for succeeded, failed, and skipped audits.
- Reuse the existing audit list loader and pagination state.
- Keep existing standalone list filter buttons unchanged.

## TDD Steps

1. RED: Add a frontend test that loads summary and clicks the failed count drilldown.
2. GREEN: Render summary drilldown buttons that call the existing audit list loader.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.

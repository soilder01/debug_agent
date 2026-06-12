# Frontend Hide Skipped Writeback Retry

## Goal

Prevent misleading direct retries for skipped writeback audits because skipped states usually mean a report or row mapping is missing.

## Scope

- Show `Retry writeback` only for failed audits.
- Hide retry for succeeded and skipped audits.
- Preserve open job and report-link actions for all audit rows.

## TDD Steps

1. RED: Add a frontend test proving skipped audit rows do not show retry.
2. GREEN: Render retry only when `status === "failed"`.
3. VERIFY: Run focused frontend tests, full verification, diagnostics, whitespace check, and secret scan.

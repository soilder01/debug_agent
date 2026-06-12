# Runtime Auto Writeback Wiring

## Goal

Wire the worker completion hook into the backend runtime so completed spreadsheet-backed jobs can write reports back without manual clicks.

## Scope

- Add a small worker factory in the API runtime.
- Use the configured spreadsheet writeback client when available.
- Generate report links from a configurable report base URL.
- Preserve current worker behavior when no writeback client is configured.

## TDD Steps

1. RED: Add an API/runtime test proving the worker writes back after completing a mapped job.
2. GREEN: Wire the completion hook through the runtime worker factory.
3. RED: Add settings/template coverage for report base URL.
4. GREEN: Add `DEBUG_AGENT_REPORT_BASE_URL`.
5. VERIFY: Run focused tests, full verify, diagnostics, whitespace check, and secret scan.


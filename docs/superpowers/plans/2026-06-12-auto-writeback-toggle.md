# Auto Writeback Toggle

## Goal

Add an explicit runtime setting for automatic spreadsheet writeback so operators can run workers safely before enabling writes.

## Scope

- Add `DEBUG_AGENT_AUTO_WRITEBACK_ENABLED`.
- Keep automatic writeback disabled unless explicitly enabled.
- Preserve manual writeback API behavior.
- Surface the toggle through worker runtime status.

## TDD Steps

1. RED: Add settings tests for the auto-writeback flag.
2. GREEN: Parse the flag from environment.
3. RED: Add worker factory tests for enabled and disabled behavior.
4. GREEN: Gate the completion hook behind the flag.
5. VERIFY: Run focused tests, full verification, diagnostics, whitespace check, and secret scan.


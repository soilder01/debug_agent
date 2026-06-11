# Phase 39: Evidence Parse Error Capture

## Goal

Capture malformed model outputs as evidence instead of failing the whole job, preserving raw output and parse error details for diagnosis.

## Scope

- Runner catches prediction parse errors per trial.
- Evidence records `response_parse_error`.
- Parse-error evidence receives score `0` with an explicit judge reason.
- Repository persists and restores the parse error.
- SQLite migration adds a default parse-error column for existing databases.

## Checklist

- [x] Add failing runner test for malformed model output evidence.
- [x] Add failing repository persistence and migration tests.
- [x] Implement runner parse-error capture.
- [x] Persist and restore response parse errors.
- [x] Add SQLite missing-column migration.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

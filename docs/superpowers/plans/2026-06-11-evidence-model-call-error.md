# Phase 41: Evidence Model Call Error

## Goal

Capture model adapter failures as evidence so timeout/transport/runtime failures are visible per trial instead of only appearing as job-level exceptions.

## Scope

- Runner catches adapter exceptions per trial.
- Evidence records `model_call_error_type` and `model_call_error_message`.
- Failed model calls receive score `0` with reason `model_call_error`.
- Repository persists and restores model-call error fields.
- SQLite migration adds default model-call error columns for existing databases.

## Checklist

- [x] Add failing runner test for adapter exception evidence.
- [x] Add failing repository persistence and migration tests.
- [x] Implement runner model-call error capture.
- [x] Persist and restore model-call error fields.
- [x] Add SQLite missing-column migration.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

# Phase 37: Evidence Request Summary And Latency

## Goal

Persist a safe request summary and model-call latency for each evidence item so live-model runs can be audited without storing secrets or full payloads.

## Scope

- Record prompt length and whether an image URI was provided.
- Record elapsed model-call latency in milliseconds.
- Persist both fields to SQLite evidence rows.
- Add startup migration for older local databases.

## Checklist

- [x] Add failing runner test for request summary and latency.
- [x] Add failing repository persistence and migration tests.
- [x] Implement runtime evidence fields.
- [x] Persist and restore fields through repository.
- [x] Add SQLite missing-column migration.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

# Phase 34: Evidence Provider And Model ID

## Goal

Persist the model provider and concrete model ID for every experiment evidence item so live-model debug runs remain auditable and reproducible.

## Scope

- Add focused RED tests for runtime evidence metadata.
- Persist `model_provider` and `model_id` in SQLite evidence rows.
- Add startup migration for existing local databases missing these columns.
- Keep default verification offline and deterministic.

## Checklist

- [x] Add failing experiment runner test for provider/model ID propagation.
- [x] Add failing repository persistence test for provider/model ID.
- [x] Add failing schema migration test for missing provider/model ID columns.
- [x] Implement `ModelResponse` metadata fields.
- [x] Populate metadata in fake and Ark adapters.
- [x] Persist metadata through evidence and repository.
- [x] Verify focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

# Phase 35: Job-Scoped Evidence API

## Goal

Expose persisted evidence details by `job_id` and `evidence_id` so async worker results remain queryable after they are written to SQLite.

## Scope

- Add repository retrieval for a single evidence row by composite key.
- Convert persisted rows back into `ExperimentEvidence`.
- Add `GET /jobs/{job_id}/evidence/{evidence_id:path}`.
- Keep the older case-scoped artifact route for compatibility.

## Checklist

- [x] Add failing repository test for persisted evidence retrieval.
- [x] Add failing API test for job-scoped evidence metadata.
- [x] Implement repository retrieval.
- [x] Implement job-scoped evidence route.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

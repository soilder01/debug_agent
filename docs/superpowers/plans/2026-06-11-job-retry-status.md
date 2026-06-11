# Phase 44: Job Retry Status

## Goal

Expose retry state on job status so operators can tell whether a failed or requeued job still has retry budget.

## Scope

- Add retry status calculation to `DebugJobService`.
- Add `max_attempts`, `remaining_attempts`, and `will_retry` to `GET /jobs/{job_id}`.
- Render retry status in the frontend job status panel.

## Checklist

- [x] Add failing backend API test for retry status.
- [x] Add failing frontend test for retry status display.
- [x] Implement retry status calculation.
- [x] Add API response fields.
- [x] Render retry status in frontend.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

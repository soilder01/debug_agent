# Phase 43: Job Evidence Error Summary

## Goal

Expose aggregated evidence error counts on job status so operators can identify whether a job failed due to judge mismatches, parse errors, or model-call errors without opening every evidence item.

## Scope

- Add repository aggregation for evidence issue counts.
- Add `evidence_error_counts` to `GET /jobs/{job_id}`.
- Keep the response backward-compatible by retaining existing job status fields.

## Checklist

- [x] Add failing repository test for evidence error counts.
- [x] Add failing API test for job status error summary.
- [x] Implement repository aggregation.
- [x] Add API response field.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

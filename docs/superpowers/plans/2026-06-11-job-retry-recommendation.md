# Phase 45: Job Retry Recommendation

## Goal

Expose a retry recommendation on job status so operators can distinguish retryable infrastructure/model-call failures from non-retryable parse or judgement failures.

## Scope

- Add `retry_recommendation` to `GET /jobs/{job_id}`.
- Recommend retry only when retry budget remains and model-call errors are present.
- Keep parse errors and pure judgement failures as non-retry recommendations.
- Render the recommendation in the frontend job status panel.

## Checklist

- [x] Add failing backend API tests for retry recommendations.
- [x] Add failing frontend assertion for recommendation display.
- [x] Implement recommendation calculation.
- [x] Add API response field.
- [x] Render recommendation in frontend.
- [x] Run focused tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

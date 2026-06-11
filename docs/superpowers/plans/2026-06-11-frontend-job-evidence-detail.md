# Phase 36: Frontend Job Evidence Detail

## Goal

Let users open persisted evidence details from a completed job and see model metadata in the UI.

## Scope

- Add a frontend client function for `GET /jobs/{job_id}/evidence/{evidence_id}`.
- Render evidence buttons in the job status panel.
- Fetch and display job-scoped evidence detail from the main app.
- Display model name, provider, and model ID in the evidence detail component.

## Checklist

- [x] Add failing UI test for job evidence drilldown.
- [x] Add job-scoped evidence client function and metadata types.
- [x] Render clickable evidence IDs in job status panel.
- [x] Wire App state to fetch job-scoped evidence detail.
- [x] Show model metadata in evidence detail.
- [x] Run focused frontend tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

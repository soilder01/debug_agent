# Job Status Writeback Audit

## Goal

Surface spreadsheet writeback audit summaries directly in job status and job listing APIs, then render them in the frontend job status panel.

## Scope

- Add `spreadsheet_writeback_audit` to `GET /jobs/{job_id}` and `GET /jobs`.
- Keep the field `null` when no writeback was attempted.
- Render audit status, row, and error in `JobStatusPanel`.
- Preserve the detailed audit endpoint for full fields/report URL.

## TDD Steps

1. RED: Add backend API expectations for audit summary in job status/listing.
2. GREEN: Extend response models and `_build_job_status`.
3. RED: Add frontend component expectation for audit summary rendering.
4. GREEN: Extend TypeScript types and UI rendering.
5. VERIFY: Run focused tests, full verification, diagnostics, whitespace check, and secret scan.


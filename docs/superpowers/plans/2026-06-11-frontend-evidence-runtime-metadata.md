# Phase 38: Frontend Evidence Runtime Metadata

## Goal

Show request summary and latency in the evidence detail UI so operators can inspect runtime context without opening raw database rows.

## Scope

- Extend frontend evidence type with `request_summary` and `latency_ms`.
- Render latency, prompt length, image presence, and image URI scheme.
- Cover the job-scoped evidence drilldown with a focused UI test.

## Checklist

- [x] Add failing UI assertions for request summary and latency.
- [x] Extend frontend evidence type.
- [x] Render runtime metadata in evidence detail.
- [x] Run focused frontend tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

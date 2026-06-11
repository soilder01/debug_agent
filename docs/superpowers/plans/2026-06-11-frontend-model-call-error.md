# Phase 42: Frontend Model Call Error

## Goal

Show model-call error type and message in evidence details so operators can distinguish timeouts, transport failures, and other adapter errors from parse failures.

## Scope

- Extend frontend evidence type with model-call error fields.
- Render model-call error details only when present.
- Add UI assertions in the existing job evidence drilldown test.

## Checklist

- [x] Add failing UI assertions for model-call error display.
- [x] Extend frontend evidence type.
- [x] Render model-call error fields.
- [x] Run focused frontend tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

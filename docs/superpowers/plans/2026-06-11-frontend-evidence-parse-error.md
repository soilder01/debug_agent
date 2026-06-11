# Phase 40: Frontend Evidence Parse Error

## Goal

Display response parse errors in evidence details so malformed model outputs are immediately diagnosable from the UI.

## Scope

- Extend frontend evidence type with `response_parse_error`.
- Render parse error only when present.
- Cover job-scoped evidence detail with a UI assertion.

## Checklist

- [x] Add failing UI assertion for parse error display.
- [x] Extend frontend evidence type.
- [x] Render parse error in evidence detail.
- [x] Run focused frontend tests.
- [x] Run full verification, diagnostics, and secret scan.
- [x] Commit a clean checkpoint.

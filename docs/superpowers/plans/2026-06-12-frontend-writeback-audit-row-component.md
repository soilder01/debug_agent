# Frontend Writeback Audit Row Component

## Goal

Extract spreadsheet writeback audit row rendering from `App.tsx` into a focused component to reduce main application complexity.

## Scope

- Add a `WritebackAuditRow` component for one audit row.
- Preserve row text, timestamps, retry eligibility, retry reason, field count, field details, job action, retry action, and report link behavior.
- Keep retry available only for failed audits.
- Reuse the component from `App.tsx`.

## TDD Steps

1. RED: Add component tests for failed and succeeded audit row behavior.
2. GREEN: Implement `WritebackAuditRow` and wire `App.tsx` to use it.
3. VERIFY: Run focused component/App tests, full verification, diagnostics, whitespace check, and secret scan.

# Frontend Batch Job Controls Panel

## Goal

Extract batch job input and load controls from `App.tsx`.

## Steps

1. Add a failing component test for batch ids textarea changes and submit/load actions.
2. Implement `BatchJobControlsPanel`.
3. Replace inline Batch Jobs controls in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing Batch Jobs heading, label, and button names remain unchanged.
- Textarea changes delegate full text.
- Load actions delegate status/sort intent without changing App orchestration.

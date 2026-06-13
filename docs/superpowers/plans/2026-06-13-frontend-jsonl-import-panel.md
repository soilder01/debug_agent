# Frontend JSONL Import Panel

## Goal

Extract JSONL import controls and result rendering from `App.tsx`.

## Steps

1. Add a failing component test for textarea value changes, import action, and result rendering.
2. Implement `JSONLImportPanel` using `JSONLImportResultPanel`.
3. Replace inline JSONL import JSX in `App.tsx`.
4. Run focused tests, full verification, diagnostics, secret scan, and commit.

## Acceptance

- Existing JSONL label and button text remain unchanged.
- Textarea changes delegate the full JSONL text.
- Existing JSONL import result rendering remains unchanged.

# Frontend Import Workspace

## Goal

Extract the three import sections from `App.tsx` into an `ImportWorkspace` component.

## Scope

- Compose JSONL import, CSV import, and spreadsheet rows JSON import panels.
- Preserve all existing headings, controlled values, and import actions.
- Keep parsing and API orchestration in `App`.
- Add a focused component test before implementation.

## Verification

- RED: `ImportWorkspace.test.tsx` fails because the component is missing.
- GREEN: focused import workspace test passes.
- Regression: `App.test.tsx` still passes.
- Full: run repository verification, diagnostics, whitespace check, and secret scan before commit.

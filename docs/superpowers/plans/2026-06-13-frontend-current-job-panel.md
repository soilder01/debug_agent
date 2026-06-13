# Frontend Current Job Panel

## Goal

Extract the current job status and selected evidence rendering from `App.tsx` into a focused `CurrentJobPanel`.

## Scope

- Compose `JobStatusPanel` and `EvidenceDetail`.
- Preserve persisted report loading and evidence selection actions.
- Keep job polling, report loading, and evidence fetching in `App`.
- Add a focused component test before implementation.

## Verification

- RED: `CurrentJobPanel.test.tsx` fails because the component is missing.
- GREEN: focused current job panel test passes.
- Regression: `App.test.tsx` still passes.
- Full: run repository verification, diagnostics, whitespace check, and secret scan before commit.

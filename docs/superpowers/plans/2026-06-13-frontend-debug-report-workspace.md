# Frontend Debug Report Workspace

## Goal

Extract the current debug report rendering area from `App.tsx` into a focused `DebugReportWorkspace` component.

## Scope

- Compose case metadata, experiment timeline, selected evidence detail, report summary, and spreadsheet writeback controls.
- Preserve the guard that writeback controls are shown only when the report has a `job_id`.
- Keep report loading, evidence loading, and writeback API orchestration in `App`.
- Add a focused component test before implementation.

## Verification

- RED: `DebugReportWorkspace.test.tsx` fails because the component is missing.
- GREEN: focused workspace test passes.
- Regression: `App.test.tsx` still passes.
- Full: run repository verification, diagnostics, whitespace check, and secret scan before commit.

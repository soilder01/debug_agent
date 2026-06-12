# Frontend Open Job From Writeback Audit

## Goal

Let operators jump from a writeback audit row directly to the corresponding job status, report, and evidence workflow.

## Scope

- Add an `Open audit job` action for each writeback audit row.
- Fetch the selected job status using the existing job API client.
- Reuse the existing `JobStatusPanel` rendering path.
- Preserve audit list pagination behavior.

## TDD Steps

1. RED: Add a frontend test for opening a job from a writeback audit row.
2. GREEN: Add the row-level action and reuse existing job status state.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.


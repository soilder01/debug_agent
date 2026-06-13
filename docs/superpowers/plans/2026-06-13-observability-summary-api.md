# Observability Summary API

## Goal

Add a backend observability summary endpoint that aggregates runtime health and operational counts for the long-running debug agent workflow.

## Scope

- Expose job status distribution and total job count.
- Expose worker runtime status in the same response.
- Expose spreadsheet writeback audit distribution and total audit count.
- Expose key operational counters such as pending backlog and failed jobs.
- Expose aggregate evidence quality metrics for debugging reliability.
- Expose health level and risk reasons for fast operational triage.
- Expose operator action suggestions for each health risk.
- Keep this slice read-only and safe.

## Verification

- RED: API test fails because `/observability/summary` does not exist.
- GREEN: focused API test passes.
- Regression: full `verify.ps1`, diagnostics, whitespace check, and secret scan pass before commit.

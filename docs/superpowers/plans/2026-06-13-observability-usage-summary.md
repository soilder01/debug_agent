# Observability Usage Summary

## Goal

Add a lightweight usage and cost summary to observability so long-running agent workloads can be monitored before adding hard budget controls.

## Scope

- Aggregate model call count from persisted evidence.
- Aggregate prompt character counts from evidence request summaries.
- Expose deterministic estimated cost units as a safe placeholder metric.
- Render usage metrics in the frontend observability panel.

## Verification

- RED: backend and frontend tests fail because usage metrics are missing.
- GREEN: focused tests pass.
- Full: run `verify.ps1`, diagnostics, whitespace check, and secret scan before commit.

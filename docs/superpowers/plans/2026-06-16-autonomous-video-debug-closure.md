# Autonomous Video Debug Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the video debug agent from one-pass reporting to an autonomous closure loop that probes failing segments, compares original badcase against live reruns, plans follow-ups, assigns final attribution, verifies recommendations, writes back Chinese conclusions, and visualizes the probe lineage.

**Architecture:** Add a backend auto-closure orchestration layer that consumes an initial completed job report and creates/runs follow-up jobs through existing job service/repository primitives. Keep evidence/report schemas compatible with existing frontend components while adding explicit auto-closure results, final attribution candidates, verification outcomes, and spreadsheet writeback summaries.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy repository, Pydantic v2, pytest, React/Vitest, existing Ark video adapter and spreadsheet writeback pipeline.

---

## Completion Definition

- [x] Initial video timestamp failures automatically create and run targeted probes for failing segments.
- [x] Unstable live reruns automatically create and run stability follow-up verification.
- [x] Reports compare original spreadsheet badcase output against live rerun evidence.
- [x] Reports produce final attribution candidates: model capability gap, prompt issue, scoring asset issue, golden/reference issue, data issue, or model instability.
- [x] Recommended actions are automatically marked for verification and verification jobs are created.
- [x] Spreadsheet writeback receives Chinese root cause, evaluation feedback, evidence/report link, and auto-closure status.
- [x] Frontend visualizes auto-closure lineage and follow-up probe outcomes.
- [x] Real JSZN-131 auto-closure run proves the agent actively deepens instead of stopping after one report.
- [x] Focused tests, full `.\scripts\verify.ps1`, `git diff --check`, and secret scan pass.

## Task 1: Auto-Closure Backend Core

- [x] Add `backend/src/debug_agent/jobs/auto_closure.py`.
- [x] Add tests for automatic targeted probe creation and immediate execution.
- [x] Reuse `save_targeted_probe_job`, `submit_case_debug`, and `run_job`.

## Task 2: Badcase vs Live Comparison

- [x] Detect original predictions from imported case.
- [x] Compare original timestamp deltas with live evidence deltas.
- [x] Classify `model_instability` when live rerun succeeds but original badcase failed.

## Task 3: Stability Follow-Up Planner

- [x] Detect partial pass rate such as `4/5`.
- [x] Create and run stability verification follow-up.
- [x] Preserve lineage in strategy follow-up history.

## Task 4: Final Attribution Candidates

- [x] Generate final attribution candidates without requiring human handoff.
- [x] Include category, confidence, evidence ids, artifact ids, and Chinese explanation.
- [x] Convert final attribution into recommended action verification.

## Task 5: Auto Verification and Writeback

- [x] Automatically create verification jobs for high-priority actions.
- [x] Auto-write Chinese summary fields to mapped spreadsheet rows when writeback client exists.
- [x] Save audit status for closure runs.

## Task 6: Frontend Closure Lineage

- [x] Show auto-closure results in report workspace.
- [x] Show targeted probe lineage, final attribution candidates, verification state, and writeback state.

## Task 7: Real JSZN-131 Closure Validation

- [x] Run real JSZN-131 live job.
- [x] Run auto-closure.
- [x] Confirm targeted probes and stability follow-up are created and completed.
- [x] Confirm final attribution and verification candidates are present.
- [x] Confirm Chinese report and writeback fields are actionable.

## Real JSZN-131 Auto-Closure Validation

- Source job: `6d4b2238-16c6-48af-85b7-ca3026814d15`
- Source row: `qJAomX!2`
- Video proxy: `.tmp/JSZN-131-debug-proxy.mp4` generated from the original 51.6MB attachment to avoid Ark TLS EOF on oversized base64 payloads.
- Live evidence: `model_call_errors=0`, `success_count=4`, `total_trials=9`, root cause `video_timestamp_boundary_error`.
- Auto targeted probes: `b7afdcaa-1112-4fe0-bc3c-9a2c58267b6b`, `a7cf6f25-f1c2-451b-a9d5-43aa70453add`, `bf3a9f80-2003-46a5-963a-88e5ed9e6142`.
- Auto stability follow-up: `61a37674-29b1-4b5b-91a5-a50dda17c402`.
- Auto verification jobs: `397621d4-ce35-4f11-a488-47bbc40f9097`, `f4a9f4df-8297-493f-83d3-c820e9df1bc8`.
- Final attribution candidate: `model_instability/high`, because original badcase was `0/1` while live rerun reached `4/9`.
- Spreadsheet writeback: `succeeded`; row 2 received Chinese root cause, evaluation feedback, report link, auto-closure status, probe evidence, original-vs-live comparison, and final attribution candidate.

## Personal Perfect-Use Gap Closure

The previous validation proved the agent can run real auto-closure, but personal-use quality is not yet `100%` because the report and probes must be directly trustworthy without terminal reconstruction.

- [x] Auto-closure result now carries `evidence_summaries` with source/follow-up/verification `job_id`, `evidence_id`, step, trial, judge score, delta reasons, raw output excerpt, and error fields.
- [x] Frontend report panel renders auto-closure evidence summaries instead of only job ids.
- [x] Local and Lark final report were regenerated from real JSZN-131 auto-closure evidence and U2 was updated to the new report URL.
- [x] Targeted probe now creates a dedicated targeted case and prompt from the failing segment/window instead of blindly reusing the full source case.
- [x] Production auto-closure API now has a local ffmpeg video clipper for failing segment windows when the source video is local and available.
- [x] Structured-output artifacts now persist the full raw model output to disk and expose `derived_uri`.
- [x] Full raw output is now persisted as structured-output artifacts with `derived_uri`; request prompt and clipped video URI are carried in input/targeted case metadata for drilldown follow-up.
- [x] Targeted probe now uses a dedicated clipped-window case and prompt; result evidence summaries show whether each follow-up evidence passed or failed.
- [x] Final report content generation is now reusable through `build_auto_closure_markdown_report()` and includes COT, original prediction, scoring rules, deepening lineage, targeted outcomes, and evidence raw-output excerpts.
- [x] Re-run full `.\scripts\verify.ps1`, `git diff --check`, and secret scan after the personal-perfect gap closure changes.

## Latest Verification

- Focused backend: `47 passed`.
- Focused frontend auto-closure: `4 passed`.
- Full `.\scripts\verify.ps1`: backend `362 passed, 1 skipped`; frontend `179 passed`; backend/frontend lint and typecheck passed.
- `git diff --check`: passed.
- Secret scan on tracked diff excluding local artifacts/temp outputs: no Ark key found.

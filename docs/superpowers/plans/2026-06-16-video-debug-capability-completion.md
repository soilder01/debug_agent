# Video Debug Capability Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the agent complete real video debug tasks end-to-end on JSZN-131-quality spreadsheet rows, with live video model calls, native timestamp judging, evidence-rich Chinese reports, and reliable writeback fields.

**Architecture:** Keep the existing job/evidence/report pipeline, but add native video-action parsing and timestamp-grid judging instead of forcing spreadsheet outputs through generic label comparison. Evidence artifacts must carry per-segment expected/actual time windows, and reports must distinguish model temporal failures from evaluation-asset problems.

**Tech Stack:** Python 3.11, FastAPI/TestClient, Pydantic v2, pytest, Ark video adapter, existing Lark spreadsheet import/writeback pipeline.

---

## Completion Definition

- [x] JSZN-131 can be imported from spreadsheet-shaped row data without manual schema hacks.
- [x] Live `ark-video` jobs can send local video files using Ark-supported input URLs.
- [x] Model output in `video_action_segments` format is parsed natively.
- [x] `check_timestamp` ops with `range` and `continue` rules are judged natively.
- [x] Reports include segment-level Chinese debug conclusions and recommended actions.
- [x] Writeback fields include concise Chinese root cause, evaluation feedback, and report link.
- [x] Frontend report/evidence surfaces can display timestamp deltas without label-noise.
- [x] Focused tests, full `.\scripts\verify.ps1`, `git diff --check`, and secret scan pass.
- [x] A real JSZN-131 live run produces `model_call_errors=0`, meaningful timestamp deltas, and a Chinese report that can guide a human debugger.

## File Map

- Modify: `backend/src/debug_agent/cases/models.py` for optional video timestamp scoring structures if needed.
- Modify: `backend/src/debug_agent/cases/comparator.py` for native `video_action_segments` parsing and timestamp delta support.
- Modify: `backend/src/debug_agent/judging/runner.py` for `check_timestamp` range/continue evaluation.
- Modify: `backend/src/debug_agent/experiments/runner.py` for evidence artifacts with timestamp metadata.
- Modify: `backend/src/debug_agent/reports/generator.py` for video-specific root cause, trace, actions, and suggested fields.
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py` for Chinese-friendly writeback feedback.
- Modify: `backend/src/debug_agent/imports/csv_cases.py` and `backend/src/debug_agent/imports/spreadsheet_rows.py` for JSZN-style column aliases.
- Modify: `frontend/src/reports/ReportPanel.tsx` and `frontend/src/evidence/EvidenceDetail.tsx` only after backend fields stabilize.
- Test: `backend/tests/judging/test_runner.py`, `backend/tests/cases/test_comparator.py`, `backend/tests/imports/test_spreadsheet_rows.py`, `backend/tests/reports/test_generator.py`, `backend/tests/spreadsheets/test_writeback.py`, focused frontend tests if UI changes.

## Task 1: Native Video Action Parsing

- [x] Add RED tests proving `video_action_segments` output parses into `VideoDetectionOutput`.
- [x] Implement minimal parser support for `subtask_label`, `start_s`, and `end_s`.
- [x] Preserve existing `temporal_segments` parser behavior.
- [x] Run focused comparator/judging tests.

## Task 2: Timestamp Grid Judge

- [x] Add RED tests for `check_timestamp` range and continue rules using JSZN-131 segment windows.
- [x] Implement scoring-op parser from JSON scoring standards.
- [x] Judge each predicted segment by `start_s`/`end_s`, not label text hacks.
- [x] Emit deltas with reason codes such as `timestamp_end_out_of_range`, `timestamp_start_not_continuous`, `missing_segment`, and `extra_segment`.
- [x] Run focused judging tests.

## Task 3: Spreadsheet Row Compatibility

- [x] Add RED tests for JSZN-style columns: `id`, `user prompt`, `参考答案`, `predict`, `score`, `gpt_response`, `video`, `chains_alpha`, and `评分标准（详细版）`.
- [x] Map JSZN rows into `DebugCase(task_type="video_detection")`.
- [x] Store `check_timestamp` ops in `scoring_standard` or `expected_output` without losing raw text.
- [x] Run spreadsheet import tests.

## Task 4: Evidence Artifacts

- [x] Add RED tests for video timestamp delta artifact metadata.
- [x] Include `expected_start_s`, `expected_end_min_s`, `expected_end_max_s`, `actual_start_s`, `actual_end_s`, and `delta_seconds`.
- [x] Keep keyframe manifest generation working.
- [x] Run experiment runner tests.

## Task 5: Chinese Report Quality

- [x] Add RED tests requiring video timestamp root cause traces and recommended actions.
- [x] Generate Chinese summaries that identify model failure vs evaluation-asset risk.
- [x] Include a compact segment-delta table in suggested sheet fields.
- [x] Run report generator/writeback tests.

## Task 6: Frontend Display

- [x] Add RED tests for timestamp delta display in evidence/report panels.
- [x] Render expected vs actual time ranges, per-segment pass/fail, and Chinese root-cause snippets.
- [x] Run focused frontend tests.

## Task 7: Real JSZN-131 Live Validation

- [x] Run the real `ark-video` JSZN-131 job with downloaded video.
- [x] Confirm `model_call_errors=0`.
- [x] Confirm report contains native timestamp deltas instead of label-mismatch noise.
- [x] Confirm Chinese report is human-debugger friendly.
- [x] Run full verification and commit.

## Final Validation

- Focused backend set: `101 passed`.
- Focused frontend set: `28 passed`.
- Full `.\scripts\verify.ps1`: backend `352 passed, 1 skipped`; frontend `175 passed`; backend/frontend lint and typecheck passed.
- Real JSZN-131 live job: `9d42f86c-f15e-4102-a86b-7adf61836072`, `model_call_errors=0`, `success_count=4`, `failed_trial_count=1`, root cause `video_timestamp_boundary_error`.

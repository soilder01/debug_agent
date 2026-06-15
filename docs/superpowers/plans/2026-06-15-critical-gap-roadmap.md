# Critical Gap Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining critical gaps from the harness-first Debug Agent roadmap: verification evaluation, real multimodal evidence, adaptive planning, confidence reasoning, and production governance.

**Architecture:** Keep the current harness-native report/evidence/action lineage as the core spine. Add small, auditable capabilities around it: evaluate verification jobs, enrich video artifacts, generate follow-up experiment plans, explain confidence, and harden governance.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, pytest, React 18, TypeScript, Vitest.

---

## Critical Gap Roadmap

### P0: Verification Result Evaluation

- Goal: turn `applied -> verification job` into `applied -> verification job -> resolved/not_resolved/regressed/inconclusive`.
- Backend should evaluate verification job reports against the source job report using success rate, root cause label, and job completion state.
- Frontend should render verification result status next to each recommended action verification job.
- Writeback should eventually include verification result summaries.

### P0: Real Video Evidence Artifacts

- Goal: upgrade video manifest artifacts into visible keyframe thumbnails and eventually short segment clips.
- Start with deterministic keyframe thumbnail metadata and artifact URLs; keep ffmpeg optional so tests stay hermetic.
- Render keyframe artifacts in `EvidenceDetail` beside video segment manifests.

### P1: Adaptive Experiment Planner

- Goal: create next-round probing plans from root cause trace and verification results.
- Start with rule-based planner extensions for unresolved/regressed verification results.
- Keep recipes task-native and avoid OCR-shaped assumptions.

### P1: Root Cause Confidence Evidence

- Goal: make report confidence explainable with source evidence counts, ablation patterns, and verification outcomes.
- Add structured confidence reasons instead of only a `high/medium` string.

### P2: Production Governance

- Goal: make actor identity, permissions, cancellation, budget policy, and audit export production-ready.
- Start by replacing free-form frontend actor strings with trusted actor source when auth is available.

### Task 1: Verification Result Evaluation

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/tests/api/test_recommended_action_status.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add backend verification result evaluation for each recommended action verification.
- [x] Return `verification_results` from `GET /jobs/{job_id}/recommended-actions/statuses`.
- [x] Classify completed verification jobs as `resolved`, `not_resolved`, `regressed`, or `inconclusive`.
- [x] Keep incomplete verification jobs as `pending`.
- [x] Render verification result status in the frontend report panel.
- [x] Run focused backend API and frontend API/report tests.

### Task 2: Video Keyframe Evidence Artifacts

**Files:**
- Modify: `backend/src/debug_agent/artifacts/videos.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] Add deterministic keyframe thumbnail artifact metadata for video segment deltas.
- [x] Expose keyframe artifact URLs alongside video segment manifests.
- [x] Render keyframe artifact links in Evidence Detail.
- [x] Keep video artifact generation hermetic without requiring ffmpeg in tests.

### Task 3: Verification-Aware Experiment Planning

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/reports/test_generator.py`

- [x] Add follow-up experiment recommendations for unresolved or regressed verification results.
- [x] Preserve task-native recipe routing for image, video, text, and multimodal tasks.
- [x] Include follow-up plan summary in reports.

### Task 4: Root Cause Confidence Reasons

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add structured confidence reasons to `DebugReport`.
- [x] Include evidence counts, ablation patterns, and verification outcomes as confidence inputs.
- [x] Render confidence reasons in the report panel.

### Task 5: Production Governance Baseline

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/app/App.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/app/App.test.tsx`

- [x] Centralize actor defaults for recommended action status and verification requests.
- [x] Reject empty actor values once trusted actor source is configured.
- [x] Keep local development fallback actor explicit and auditable.

### Task 6: Verification Result Writeback Trace

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Test: `backend/tests/reports/test_generator.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] Persist recommended action verification results on `DebugReport`.
- [x] Rebuild verification result summaries from saved verification lineage.
- [x] Include verification result summaries in spreadsheet `评估问题反馈`.

### Task 7: Explainable Root Cause Trace

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add structured `hypothesis`, `observation`, `conclusion`, and `next_probe` fields to root cause trace items.
- [x] Keep evidence, target, delta, and artifact links attached to each reasoning step.
- [x] Render the richer reasoning trace in the frontend report panel.

### Task 8: Evaluation Asset Diagnostics

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add structured diagnostics for prompt, golden/expected output, and scoring standard issues.
- [x] Generate recommended actions for evaluation asset root causes.
- [x] Render evaluation asset diagnostics in the frontend report panel.

### Task 9: Evidence Citation Coverage Governance

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Attach evidence, artifact, and trace references to recommended actions.
- [x] Attach evidence, artifact, and trace references to confidence reasons.
- [x] Attach evidence, artifact, and trace references to evaluation asset diagnostics.
- [x] Render citation coverage in the frontend report panel.

### Task 10: Debug Report Explainability Workspace

**Files:**
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Add a top-level explainability workspace narrative.
- [x] Summarize evidence spine, diagnostics, confidence, recommended action, verification result, and next probe.
- [x] Preserve the detailed report panel as the drill-down view.

### Task 11: Multi-Step Root Cause Strategy Planner

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add structured `debug_strategy` stages to reports.
- [x] Include objective, trigger, planned probe, stop condition, and escalation for each strategy stage.
- [x] Render debug strategy stages in the frontend report panel.

### Task 12: Strategy-Aware Follow-Up Experiment Generation

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Convert debug strategy stages into executable follow-up experiment steps.
- [x] Include strategy-driven follow-up experiments in `DebugReport`.
- [x] Render strategy-driven follow-up experiments in the frontend report panel.

### Task 13: Strategy Follow-Up Job Submission

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add a strategy follow-up job lineage table and repository methods.
- [x] Add API endpoints to create and list strategy follow-up debug jobs.
- [x] Add frontend API/client support and report panel action buttons.
- [x] Wire strategy follow-up job creation into the main app flow.

### Task 14: Strategy Follow-Up Job History Workspace

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Add frontend API support for listing strategy follow-up job lineage.
- [x] Load strategy follow-up history when opening a persisted report with follow-up plans.
- [x] Render strategy follow-up job history in the report workspace.
- [x] Allow operators to open persisted strategy follow-up jobs from the history panel.

### Task 15: Strategy Follow-Up Outcome Evaluation

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Evaluate strategy follow-up job outcome from job status and evidence success rate.
- [x] Classify follow-ups as `pending`, `passed_stop_condition`, or `needs_escalation`.
- [x] Return outcome summary, success rate, and escalation recommendation in follow-up history.
- [x] Render strategy outcome evaluation in the report workspace.

### Task 16: Strategy Outcome Writeback Trace

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] Promote strategy follow-up outcomes into rebuilt `DebugReport`.
- [x] Reuse one backend strategy outcome builder across report and API responses.
- [x] Include strategy follow-up outcome and escalation summaries in spreadsheet `评估问题反馈`.
- [x] Keep strategy outcome writeback derived from current job/evidence state instead of stale persisted fields.

### Task 17: Escalation-Aware Next Probe Planning

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/reports/test_job_report.py`

- [x] Convert `needs_escalation` strategy outcomes into executable next probing steps.
- [x] Add a single-modality escalation probe for failed `ablation_expansion` follow-up outcomes.
- [x] Append escalation-driven follow-up experiments to rebuilt reports.
- [x] Preserve base recipe routing while adding escalation probes only when stop conditions fail.

### Task 18: Escalation Follow-Up Job Submission

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Allow `strategy_outcome` escalation follow-up experiments to create debug jobs.
- [x] Prefer escalation-derived planned steps over original debug strategy planned steps when both share the same stage.
- [x] Render runnable controls for escalation follow-up experiments in the report panel.
- [x] Preserve existing debug strategy follow-up submission behavior.

### Task 19: Strategy Feedback Loop Automation

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] Detect when a completed job is a strategy follow-up job.
- [x] Resolve the source job from strategy follow-up lineage.
- [x] Automatically rebuild and write back the source job report when a strategy follow-up completes.
- [x] Keep normal completed job writeback behavior unchanged.

### Task 20: Strategy Feedback Observability

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`

- [x] Add strategy follow-up feedback counts to observability summary.
- [x] Track total, pending, passed stop condition, and needs escalation counts.
- [x] Surface `needs_escalation` as a degraded health reason with an operator action.
- [x] Render strategy feedback metrics in the observability panel.

### Task 21: Targeted Region/Segment Probe Planner

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/reports/test_generator.py`

- [x] Generate targeted probe steps from root cause trace target ids.
- [x] Add image region, video segment, and multimodal conflict targeted probe types.
- [x] Include targeted probe follow-up experiments in generated reports.
- [x] Preserve existing debug strategy follow-ups while appending target-level probes.

### Task 22: Targeted Probe Job Submission

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/reports/test_generator.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add targeted probe job lineage persistence for source job, target id, planned steps, actor, and note.
- [x] Add API endpoint to create traceable targeted probe debug jobs from report follow-up entries.
- [x] Extract target ids from both structured judge deltas and semi-structured judge reasons.
- [x] Add frontend API/client support and runnable targeted probe buttons.
- [x] Wire targeted probe creation into the main app flow and show the created job.

### Task 23: Targeted Probe History and Outcome Evaluation

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Add API endpoint to list targeted probe job lineage for a source job.
- [x] Evaluate targeted probe outcomes as `pending`, `target_cleared`, `target_still_failing`, or `inconclusive`.
- [x] Include success rate, summary, and escalation guidance for targeted probe history.
- [x] Add frontend API/client support for targeted probe history.
- [x] Render targeted probe job history in the report workspace and allow opening probe jobs.

### Task 24: Targeted Probe Outcome Writeback Trace

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] Promote targeted probe outcomes into rebuilt `DebugReport`.
- [x] Reuse one backend targeted probe outcome builder across report and API responses.
- [x] Include targeted probe outcome and escalation summaries in spreadsheet `评估问题反馈`.
- [x] Automatically rebuild and write back the source job report when a targeted probe job completes.
- [x] Keep strategy follow-up writeback behavior unchanged.

### Task 25: Targeted Probe Feedback Observability

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] Add targeted probe feedback counts to observability summary.
- [x] Track total, pending, target cleared, target still failing, and inconclusive counts.
- [x] Surface target still failing probes as a degraded health reason with an operator action.
- [x] Render targeted probe metrics in the observability panel.
- [x] Preserve compatibility with older frontend summary mocks through fallback defaults.

### Task 26: Targeted Probe Escalation Planning

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Convert `target_still_failing` and `inconclusive` targeted probe outcomes into executable escalation steps.
- [x] Add image region, video segment, and multimodal conflict escalation probe names.
- [x] Append targeted outcome escalation follow-up experiments to rebuilt reports.
- [x] Allow targeted outcome follow-up experiments to create another targeted probe job.
- [x] Preserve cleared targeted probes as terminal outcomes with no escalation follow-up.

### Task 27: Targeted Probe Escalation Job Lineage

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Add lineage fields for targeted probe source, parent probe job, and trigger outcome.
- [x] Persist normal targeted probes as `source=targeted_probe`.
- [x] Persist escalation targeted probes as `source=targeted_probe_outcome`.
- [x] Prefer targeted outcome follow-up entries when creating another probe for an already-failed target.
- [x] Keep frontend targeted probe history and report loading compatible with escalation follow-up sources.

### Task 28: Targeted Probe Escalation Observability Drilldown

**Files:**
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`

- [x] Add a targeted probe escalation chain drilldown in the report workspace.
- [x] Group targeted probe jobs by target id and order parent/child probe lineage.
- [x] Render chain depth for repeated target-level probing.
- [x] Render parent probe job id and trigger outcome for escalation probes.
- [x] Keep the existing flat targeted probe history available for detailed job actions.

### Task 29: Targeted Probe Loop Guardrails

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Stop automatic targeted escalation when a target reaches max probe depth.
- [x] Generate `targeted_probe_guardrail` follow-up entries with explicit stop condition.
- [x] Return a 409 response when operators try to submit a probe blocked by guardrails.
- [x] Debounce repeated target escalation by only escalating the latest probe in each target chain.
- [x] Render targeted probe guardrail stop conditions without runnable probe actions.

### Task 30: Targeted Probe Guardrail Writeback and Observability

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`

- [x] Include targeted probe guardrail stop conditions in spreadsheet `评估问题反馈`.
- [x] Add max-depth reached counts to targeted probe observability summary.
- [x] Surface targeted probe guardrails as a degraded health reason.
- [x] Add operator action guidance for guardrail-triggered human investigation.
- [x] Render targeted max-depth metrics in the observability panel.

### Task 31: Targeted Probe Human Handoff

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add structured human handoff requests to `DebugReport`.
- [x] Convert targeted probe guardrail follow-ups into high-priority human handoff tasks.
- [x] Include target id, reason, summary, owner, and next action for each handoff request.
- [x] Include human handoff requests in spreadsheet `评估问题反馈`.
- [x] Render human handoff requests in the frontend report panel.

### Task 32: Human Handoff Governance

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`

- [x] Add persistent status governance for human handoff requests.
- [x] Add API endpoints to update and list human handoff status by target id.
- [x] Reject status updates for targets that are not present in rebuilt report handoff requests.
- [x] Add human handoff status counts to observability summary and health guidance.
- [x] Add frontend API support and observability metrics for human handoff queues.

### Task 33: Human Handoff Report Workflow

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Load human handoff statuses when opening a persisted debug report with handoff requests.
- [x] Render current handoff status, actor, and note beside each handoff request.
- [x] Add report-level actions to acknowledge, start, and resolve a handoff.
- [x] Wire report-level handoff actions through `DebugReportWorkspace`.
- [x] Update App state after handoff status PATCH responses so operators see the new status immediately.

### Task 34: Human Handoff Resolution Writeback

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Include persisted human handoff statuses in rebuilt `DebugReport`.
- [x] Surface resolved handoff actor and conclusion note in report rendering.
- [x] Include human handoff status and final conclusion in spreadsheet `评估问题反馈`.
- [x] Keep report panel compatible with status data embedded directly in report payloads.
- [x] Preserve external handoff status props as the live UI override path.

### Task 35: Final Attribution Summary

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Derive final attribution entries from resolved or closed human handoff conclusions.
- [x] Classify final attribution into prompt, evaluation asset, data, model capability, or human-confirmed root cause categories.
- [x] Attach target id, status, actor, summary, and recommended next action to final attribution entries.
- [x] Include final attribution summaries in spreadsheet `评估问题反馈`.
- [x] Render final attribution summaries in the report panel.

### Task 36: Attribution-Driven Follow-Up Actions

**Files:**
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Test: `backend/tests/reports/test_job_report.py`

- [x] Convert final attribution entries into actionable recommended actions.
- [x] Map prompt issues to prompt patch recommendations.
- [x] Map evaluation asset, data, model capability, and human-confirmed categories to targeted action categories.
- [x] Generate final-attribution follow-up verification entries with category-specific planned steps.
- [x] Preserve existing recommended actions and follow-up experiments while appending attribution-driven entries.

### Task 37: Executable Final Attribution Verification

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/DebugReportWorkspace.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add an API endpoint to submit final-attribution verification jobs from report follow-up entries.
- [x] Persist final-attribution verification jobs through existing follow-up lineage with an explicit `final_attribution:<target_id>` stage.
- [x] Add frontend client support for final-attribution verification job submission.
- [x] Render runnable final-attribution follow-up buttons in report panels.
- [x] Wire App submission flow so operators can create and open the verification job from the report.

### Task 38: Final Attribution Verification Outcome

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Evaluate `final_attribution:<target_id>` follow-up jobs as final attribution verification results.
- [x] Classify completed verification jobs as `resolved`, `not_resolved`, or `inconclusive`.
- [x] Keep incomplete final attribution verification jobs as `pending`.
- [x] Include final attribution verification results in spreadsheet `评估问题反馈`.
- [x] Render final attribution verification results in the report panel.

### Task 39: Final Attribution Verification Observability

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`

- [x] Add final-attribution verification feedback metrics to observability summary responses.
- [x] Count `final_attribution:<target_id>` follow-up outcomes as pending, resolved, not resolved, or inconclusive.
- [x] Degrade observability health when final-attribution verification results remain not resolved.
- [x] Add an operator action for unresolved final-attribution verification results.
- [x] Render final-attribution verification observability metrics in the frontend panel.

### Task 40: Final Attribution Verification Recovery Loop

**Files:**
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Test: `backend/tests/reports/test_job_report.py`

- [x] Convert unresolved final-attribution verification outcomes into recovery recommended actions.
- [x] Generate follow-up recovery probes when final attribution verification remains not resolved.
- [x] Generate evidence-audit recovery steps when final attribution verification is inconclusive.
- [x] Preserve resolved and pending verification outcomes without unnecessary recovery actions.
- [x] Keep recovery entries attached to target id, category, result, and verification job lineage.

### Task 41: Executable Final Attribution Recovery

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/DebugReportWorkspace.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/api/test_recommended_action_status.py`
- Test: `frontend/src/api/client.test.ts`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Add an API endpoint to submit final-attribution recovery jobs from unresolved verification follow-ups.
- [x] Persist recovery jobs through strategy follow-up lineage with `final_attribution_recovery:<target_id>`.
- [x] Add frontend client support for final-attribution recovery job submission.
- [x] Render runnable recovery buttons for `final_attribution_verification_outcome` follow-ups.
- [x] Wire App submission flow so operators can create and open recovery jobs from reports.

### Task 42: Final Attribution Recovery Outcome Reporting

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Modify: `backend/src/debug_agent/reports/job_report.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Test: `backend/tests/reports/test_job_report.py`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Evaluate `final_attribution_recovery:<target_id>` follow-up jobs as final attribution recovery results.
- [x] Classify successful recovery jobs as `closed` and failed recovery jobs as `reopen`.
- [x] Keep pending or inconclusive recovery jobs visible as structured report results.
- [x] Add closure recommended actions when recovery jobs close the attribution loop.
- [x] Render final-attribution recovery results in the report panel.

### Task 43: Recovery Outcome Operations Loop

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/observability/ObservabilitySummaryPanel.tsx`
- Test: `backend/tests/api/test_observability_summary.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`
- Test: `frontend/src/observability/ObservabilitySummaryPanel.test.tsx`

- [x] Add final-attribution recovery feedback metrics to observability summary responses.
- [x] Count recovery outcomes as pending, closed, reopen, or inconclusive.
- [x] Degrade observability health when recovery outcomes reopen attribution review.
- [x] Add operator action for reopened final-attribution recovery results.
- [x] Include final-attribution recovery results in spreadsheet `评估问题反馈`.
- [x] Render final-attribution recovery observability metrics in the frontend panel.

## Verification Policy

Every task must follow:

```powershell
python -m pytest <focused backend tests>
npx --yes pnpm@9.15.4 --dir frontend test -- --run <focused frontend tests>
.\scripts\verify.ps1
git diff --check
git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Only commit after focused and full verification pass.

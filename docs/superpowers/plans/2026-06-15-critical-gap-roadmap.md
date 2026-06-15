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

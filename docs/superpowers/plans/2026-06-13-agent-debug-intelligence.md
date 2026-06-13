# Agent Debug Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the core Agent debug intelligence before continuing broader enterprise-hardening work.

**Architecture:** Promote scoring standard, structured answer deltas, affected regions, and report reasoning into the durable evidence/report chain. Keep each step independently testable so improvements to root cause analysis can be validated without live model calls.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy/SQLite, pytest, React/TypeScript/Vitest.

---

## Priority Reset

The current priority is Agent debug intelligence, ahead of additional enterprise operations features. The product must first become meaningfully better at diagnosing handwritten OCR badcases:

- Multi-step root cause analysis.
- Region-aware evidence generation and crop strategy.
- Prompt, golden answer, and scoring-standard issue identification.
- More trustworthy analysis reports that explain why the Agent reached a conclusion.

## File Structure

- Modify `backend/src/debug_agent/judging/runner.py`
  - Add scoring-standard context to `JudgeResult`.
  - Add structured affected box IDs and answer deltas.
- Modify `backend/src/debug_agent/experiments/runner.py`
  - Pass `DebugCase.scoring_standard` into judging.
  - Include scoring-standard metadata in `request_summary`.
- Modify `backend/src/debug_agent/storage/repository.py`
  - Persist full judge metadata while remaining backward-compatible with existing `reasons_json` list rows.
- Later modify `backend/src/debug_agent/reports/generator.py`
  - Consume structured judge metadata to infer root cause dynamically.
- Later modify `frontend/src/evidence/EvidenceDetail.tsx` and `frontend/src/reports/ReportPanel.tsx`
  - Show structured scoring evidence and root-cause support.

## Task 1: Scoring Standard And Structured Judge Evidence

**Files:**
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write failing judge tests**

Add a test that expects `judge_answer()` to return `scoring_standard`, `affected_box_ids`, and structured `deltas`.

- [ ] **Step 2: Run judge tests and verify RED**

Run: `python -m pytest backend/tests/judging/test_runner.py`

Expected: fail because `JudgeResult` does not expose the new metadata.

- [ ] **Step 3: Implement minimal judge metadata**

Extend `JudgeResult` with defaulted fields and populate them from `compare_answer_sets()`.

- [ ] **Step 4: Add experiment evidence test**

Verify `run_experiments()` passes `case.scoring_standard` into judging and records `scoring_standard_present` in `request_summary`.

- [ ] **Step 5: Persist judge metadata**

Update repository save/restore so new metadata survives job evidence reconstruction while old rows storing a plain reasons list still load.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m pytest backend/tests/judging/test_runner.py backend/tests/experiments/test_runner.py backend/tests/storage/test_repository.py
```

- [ ] **Step 7: Full verification and commit**

Run:

```powershell
.\scripts\verify.ps1
git diff --check
git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Commit:

```powershell
git add backend/src/debug_agent/judging/runner.py backend/src/debug_agent/experiments/runner.py backend/src/debug_agent/storage/repository.py backend/tests/judging/test_runner.py backend/tests/experiments/test_runner.py backend/tests/storage/test_repository.py docs/superpowers/plans/2026-06-13-agent-debug-intelligence.md
git commit -m "feat(agent): structure judging evidence"
```

## Next Tasks

- Dynamic root-cause inference from judge deltas, parse errors, model-call errors, stability, and crop evidence.
- Prompt diagnostic checks for missing JSON schema constraints, ambiguous instruction, and absent scoring-standard references.
- Golden-answer diagnostic checks for missing/extra box IDs, invalid answer shape, and suspiciously empty expected values.
- Report confidence improvements with explicit evidence citations.

## Task 2: Dynamic Root Cause From Structured Evidence

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [ ] **Step 1: Write failing report tests**

Add tests requiring `generate_initial_report()` to infer affected boxes and root cause labels from structured `JudgeResult.deltas`, model-call errors, and parse errors.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest backend/tests/reports/test_generator.py
```

Expected: fail because reports still use the static `erasure_revision_failure` template.

- [ ] **Step 3: Implement minimal root-cause inference**

Add helper functions in `reports/generator.py` to inspect `ExperimentEvidence` and build `ObservedFailure`, `RootCause`, and `suggested_sheet_fields`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest backend/tests/reports/test_generator.py backend/tests/reports/test_job_report.py backend/tests/spreadsheets/test_writeback.py
```

- [ ] **Step 5: Full verification and commit**

Run full verification and commit as `feat(agent): infer root cause from evidence`.

## Task 3: Evaluation Asset Diagnostics

**Files:**
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [ ] **Step 1: Write failing diagnostic tests**

Add tests requiring `generate_initial_report()` to identify missing scoring standards, empty golden answers, and parse errors caused by prompts without JSON/schema instructions.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest backend/tests/reports/test_generator.py
```

Expected: fail because report inference only handles runtime failures and answer mismatches.

- [ ] **Step 3: Implement minimal asset diagnostics**

Pass `DebugCase` into report inference and add deterministic asset checks before model-capability root cause inference.

- [ ] **Step 4: Full verification and commit**

Run full verification and commit as `feat(agent): diagnose evaluation assets`.

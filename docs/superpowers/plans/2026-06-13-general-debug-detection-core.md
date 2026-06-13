# General Debug Detection Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the current handwriting OCR debug agent into a general debug detection platform while preserving the OCR workflow as the first supported task type.

**Architecture:** Keep the durable job/evidence/report/writeback architecture, and introduce a compatibility layer that names the core domain as generic detection cases, outputs, regions, deltas, and reports. OCR-specific schemas remain supported as adapters so existing fixtures, imports, APIs, and spreadsheet workflows keep working during migration.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy/SQLite, pytest, React/TypeScript/Vitest.

---

## Product Direction

The final target is not only handwriting OCR badcase debug. Handwriting OCR is the first vertical recipe. The reusable core must support generic model/debug detection scenarios:

- OCR answer extraction and handwritten region analysis.
- Visual object or region detection mismatch analysis.
- Classification mismatch analysis.
- Text/schema extraction validation.
- Prompt, expected-output, scoring-standard, and runtime-error diagnosis.

## Core Principles

- Keep `DebugJob`, `ExperimentEvidence`, `DebugReport`, worker, storage, observability, budget, and spreadsheet writeback as shared platform capabilities.
- Add generic names and task-type routing before replacing OCR-specific data structures.
- Maintain backward compatibility for existing `golden_answer`, `answers`, `box_id`, and `student_answer` fixtures and imports.
- Move OCR-only labels into recipes/taxonomies rather than allowing them to define the platform.
- Ensure every migration step has focused tests and full verification before commit.

## Target Domain Model

- `DetectionCase`: generic alias/wrapper for the current `DebugCase`.
- `DetectionTarget`: generic target identity replacing hard-coded `box_id` semantics.
- `DetectionOutput`: generic model output representation; OCR maps to `AnswerSet`.
- `DetectionRegion`: generic spatial or logical region; OCR maps to `BoxRegion`.
- `DetectionDelta`: generic mismatch unit with `target_id`, `expected`, `actual`, `reason`, and `metadata`.
- `DetectionReport`: generic report contract; current `DebugReport` remains compatible.

## Migration Roadmap

### Task 1: Generic Case Aliases And Task Type

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Test: `backend/tests/cases/test_models.py`

- [ ] Add `task_type: str = "handwriting_ocr"` to `DebugCase`.
- [ ] Add generic aliases `DetectionCase`, `DetectionOutput`, `DetectionRegion`, and `DetectionPrediction`.
- [ ] Verify existing handwriting fixtures still parse with default `task_type`.
- [ ] Verify a generic `classification` case can be represented without changing current APIs.
- [ ] Run focused tests and commit as `feat(core): introduce detection case aliases`.

### Task 2: Generic Delta Adapter

**Files:**
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Modify: `backend/src/debug_agent/judging/runner.py`
- Test: `backend/tests/cases/test_comparator.py`
- Test: `backend/tests/judging/test_runner.py`

- [ ] Add `DetectionDelta` with `target_id`, `expected`, `actual`, `reason`, and `metadata`.
- [ ] Convert OCR `AnswerDelta` into generic `DetectionDelta` while preserving `box_id` in metadata.
- [ ] Keep existing `JudgeResult.deltas` JSON-compatible.
- [ ] Run focused tests and commit as `feat(core): generalize detection deltas`.

### Task 3: Task-Type Recipes

**Files:**
- Create: `backend/src/debug_agent/recipes/base.py`
- Create: `backend/src/debug_agent/recipes/handwriting_ocr.py`
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/recipes/test_handwriting_ocr.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] Introduce a recipe protocol for planner steps and prompt augmentation.
- [x] Move current OCR replay/localized prompt behavior into `handwriting_ocr` recipe.
- [x] Keep default behavior identical for current fixtures.
- [x] Run focused tests and commit as `feat(core): route experiments by task recipe`.

### Task 4: Generic Evidence Artifacts

**Files:**
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/artifacts/images.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] Introduce generic artifact fields while preserving `image_artifacts`.
- [x] Support artifact kinds beyond `affected_box_candidate`, such as `context_region`, `input_snapshot`, and `structured_output`.
- [x] Update front-end display to use generic artifact labels.
- [ ] Run focused tests and commit as `feat(core): generalize evidence artifacts`.

### Task 5: Report Taxonomy Profiles

**Files:**
- Create: `backend/src/debug_agent/reports/taxonomy.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [ ] Move OCR labels like `erasure_revision_failure` into an OCR taxonomy profile.
- [ ] Add generic labels: `evaluation_asset_issue`, `model_call_error`, `parse_error`, `output_mismatch`, `unstable_prediction`.
- [ ] Keep existing report output compatible for OCR cases while allowing generic cases to avoid OCR wording.
- [ ] Run focused tests and commit as `feat(core): add report taxonomy profiles`.

### Task 6: Frontend Product Generalization

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [ ] Rename visible product copy from `Handwriting OCR Debug Agent` to `Debug Detection Agent`.
- [ ] Replace `box`-only UI wording with `target/region` wording while preserving OCR metadata display.
- [ ] Keep OCR-specific details in task profile sections.
- [ ] Run focused tests and commit as `feat(frontend): generalize detection UI copy`.

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

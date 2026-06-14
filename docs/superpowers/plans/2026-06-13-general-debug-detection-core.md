# General Debug Detection Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a general harness-based debug detection platform for image, video, text, and multimodal model failures while preserving historical OCR fixtures only as one compatibility recipe.

**Architecture:** Keep the durable job/evidence/report/writeback architecture, and make task type, modality, output schema, evidence artifacts, and report taxonomy generic first-class concepts. OCR-specific schemas remain supported only as adapters so existing fixtures, imports, APIs, and spreadsheet workflows keep working during migration.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy/SQLite, pytest, React/TypeScript/Vitest.

---

## Product Direction

The final target is a high-generalization harness debug agent, not an OCR product. OCR is only the historical fixture set that helped bootstrap the system. The reusable core must help exploit model potential through disciplined harness experiments across many model/debug scenarios:

- Image understanding failures: object/region detection, visual QA, chart/table/image-text mismatch, crop/zoom sensitivity.
- Video understanding failures: temporal grounding, frame sampling, action/event detection, subtitle/audio/visual alignment.
- Text and schema failures: extraction, classification, long-context consistency, structured output validation.
- Multimodal failures: prompt-image/video mismatch, modality conflict, tool/crop/frame evidence attribution.
- Harness-level diagnosis: replay stability, counterfactual prompts, evidence isolation, scoring-standard validation, golden-answer validation, and runtime-error diagnosis.

## Core Principles

- Keep `DebugJob`, `ExperimentEvidence`, `DebugReport`, worker, storage, observability, budget, and spreadsheet writeback as shared platform capabilities.
- Add generic names and task-type routing before replacing OCR-specific data structures.
- Maintain backward compatibility for existing `golden_answer`, `answers`, `box_id`, and `student_answer` fixtures and imports.
- Move OCR-only labels into compatibility adapters; the product surface, reports, and plans must use generic target/evidence/modality language.
- Prioritize harness engineering that reveals model capability boundaries: repeated trials, prompt perturbations, modality-specific evidence isolation, counterfactual inputs, and auditable scoring.
- Ensure every migration step has focused tests and full verification before commit.

## Target Domain Model

- `DetectionCase`: generic case wrapper for a harness debug task.
- `DetectionTarget`: generic target identity replacing hard-coded `box_id` semantics.
- `DetectionOutput`: task-native model output representation; OCR maps to `AnswerSet` only through an adapter.
- `DetectionRegion`: generic spatial, temporal, or logical region; OCR maps to `BoxRegion` only through an adapter.
- `DetectionDelta`: generic mismatch unit with `target_id`, `expected`, `actual`, `reason`, and `metadata`.
- `DetectionReport`: generic report contract; current `DebugReport` remains compatible.

## Migration Roadmap

### Task 1: Generic Case Aliases And Task Type

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Test: `backend/tests/cases/test_models.py`

- [x] Add `task_type: str = "handwriting_ocr"` to `DebugCase`.
- [x] Add generic aliases `DetectionCase`, `DetectionOutput`, `DetectionRegion`, and `DetectionPrediction`.
- [x] Verify existing handwriting fixtures still parse with default `task_type`.
- [x] Verify a generic `classification` case can be represented without changing current APIs.
- [x] Run focused tests and commit as `feat(core): introduce detection case aliases`.

### Task 2: Generic Delta Adapter

**Files:**
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Modify: `backend/src/debug_agent/judging/runner.py`
- Test: `backend/tests/cases/test_comparator.py`
- Test: `backend/tests/judging/test_runner.py`

- [x] Add `DetectionDelta` with `target_id`, `expected`, `actual`, `reason`, and `metadata`.
- [x] Convert OCR `AnswerDelta` into generic `DetectionDelta` while preserving `box_id` in metadata.
- [x] Keep existing `JudgeResult.deltas` JSON-compatible.
- [x] Run focused tests and commit as `feat(core): generalize detection deltas`.

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
- [x] Run focused tests and commit as `feat(core): generalize evidence artifacts`.

### Task 5: Report Taxonomy Profiles

**Files:**
- Create: `backend/src/debug_agent/reports/taxonomy.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/reports/test_generator.py`

- [x] Move OCR labels like `erasure_revision_failure` into an OCR taxonomy profile.
- [x] Add generic labels: `evaluation_asset_issue`, `model_call_error`, `parse_error`, `output_mismatch`, `unstable_prediction`.
- [x] Keep existing report output compatible for OCR cases while allowing generic cases to avoid OCR wording.
- [x] Run focused tests and commit as `feat(core): add report taxonomy profiles`.

### Task 6: Frontend Product Generalization

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/reports/ReportPanel.tsx`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/reports/ReportPanel.test.tsx`

- [x] Rename visible product copy from `Handwriting OCR Debug Agent` to `Debug Detection Agent`.
- [x] Replace `box`-only UI wording with `target/region` wording while preserving OCR metadata display.
- [x] Keep OCR-specific details in task profile sections.
- [x] Run focused tests and commit as `feat(frontend): generalize detection UI copy`.

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

## Completion Snapshot

- Completed the generic case, delta, recipe, artifact, report taxonomy, and UI-copy migration path.
- Historical handwriting OCR fixtures remain compatible, but are no longer the product center.
- Classification now has a dedicated recipe in the follow-up multi-recipe orchestration plan, proving non-OCR routing.
- The next priority is task-native schemas for image/video/text/multimodal outputs so the harness can evaluate model capability without OCR-shaped fields.

## Remaining Risks

- `DetectionOutput` is still partially backed by OCR-compatible fields in storage/import paths; richer task-native schemas remain active work.
- Spreadsheet import/writeback fields still preserve OCR-compatible columns such as `golden_answer_json` and `box_regions_json`.
- Logical agent capabilities are explicit, but not yet deployed as independent services.
- Video and multimodal evidence strategies are not yet implemented; current artifacts cover request/output snapshots and image crops.

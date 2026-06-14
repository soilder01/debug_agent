# Harness Native Detection Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move harness debug tasks toward modality- and task-native schemas so image, video, text, and multimodal failures can be evaluated without OCR-shaped fields.

**Architecture:** Keep `AnswerSet` only as a compatibility adapter and introduce task-native output models beside it. Add focused parse/compare/judge paths for classification first, then route runner/judge behavior through task recipes so future image, video, text, and multimodal extraction tasks can avoid OCR field names.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React/TypeScript/Vitest.

---

## Target Milestones

### Guiding Principle: Harness First, Not OCR First

- Recipes should express how to probe model capability: replay stability, perturbation, evidence isolation, counterfactual prompts, and scoring audit.
- Schemas should match the task and modality: label outputs for classification, regions for images, temporal spans for video, structured fields for extraction, and cross-modal references for multimodal tasks.
- OCR compatibility must remain for existing data, but no new generic capability should depend on `box_id` or `student_answer`.

### Task 1: Classification Output Model And Comparator

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/cases/test_comparator.py`

- [x] Add `ClassificationOutput` with `label: str` and optional `confidence: float | None`.
- [x] Add `parse_classification_output(raw_output: str)`.
- [x] Add `compare_classification_outputs(expected, predicted)` returning generic `DetectionDelta` with `target_id="label:classification"`.
- [x] Keep OCR `AnswerSet` parsing and deltas unchanged.
- [x] Run `python -m pytest backend/tests/cases/test_models.py backend/tests/cases/test_comparator.py -q`.
- [x] Commit as `feat(core): add classification output comparator`.

### Task 2: Classification Judge Path

**Files:**
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] Add `judge_classification_output()`.
- [x] Route `task_type="classification"` runner parsing and judging through classification output models.
- [x] Preserve OCR runner behavior for `handwriting_ocr`.
- [x] Run focused judge and runner tests.
- [ ] Commit as `feat(core): judge classification outputs natively`.

### Task 3: Classification Case Payload Compatibility

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/imports/*`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/imports/*`

- [ ] Add optional generic `expected_output` and `output_schema` fields while keeping `golden_answer`.
- [ ] Allow classification fixtures to carry `expected_output={"label":"positive"}`.
- [ ] Keep existing spreadsheet and JSONL OCR imports compatible.
- [ ] Commit as `feat(core): add task native expected output fields`.

### Task 4: Frontend Task-Native Case Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/cases/ImportedCaseDetailPanel.tsx`
- Test: `frontend/src/cases/ImportedCaseDetailPanel.test.tsx`

- [ ] Display `expected_output` when present.
- [ ] Keep OCR answer and region display unchanged.
- [ ] Commit as `feat(frontend): show task native expected output`.

### Task 5: Image And Video Harness Schema Roadmap

**Files:**
- Modify: `docs/superpowers/plans/2026-06-14-task-native-detection-schemas.md`

- [ ] Define image-native output examples: `regions`, `objects`, `attributes`, `relations`, and crop/zoom artifact strategies.
- [ ] Define video-native output examples: `temporal_segments`, `keyframes`, `events`, `transcript_alignment`, and frame-sampling artifact strategies.
- [ ] Define multimodal output examples: cross-modal target ids, conflict deltas, and evidence citations.
- [ ] Commit as `docs: add multimodal harness schema roadmap`.

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

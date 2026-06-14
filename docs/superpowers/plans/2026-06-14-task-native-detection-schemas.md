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
- [x] Commit as `feat(core): judge classification outputs natively`.

### Task 3: Classification Case Payload Compatibility

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/imports/*`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/imports/*`

- [x] Add optional generic `expected_output` and `output_schema` fields while keeping `golden_answer`.
- [x] Allow classification fixtures to carry `expected_output={"label":"positive"}`.
- [x] Keep existing spreadsheet and JSONL OCR imports compatible.
- [x] Commit as `feat(core): add task native expected output fields`.

### Task 4: Frontend Task-Native Case Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/cases/ImportedCaseDetailPanel.tsx`
- Test: `frontend/src/cases/ImportedCaseDetailPanel.test.tsx`

- [x] Display `expected_output` when present.
- [x] Keep OCR answer and region display unchanged.
- [x] Commit as `feat(frontend): show task native expected output`.

### Task 5: Image And Video Harness Schema Roadmap

**Files:**
- Modify: `docs/superpowers/plans/2026-06-14-task-native-detection-schemas.md`

- [x] Define image-native output examples: `regions`, `objects`, `attributes`, `relations`, and crop/zoom artifact strategies.
- [x] Define video-native output examples: `temporal_segments`, `keyframes`, `events`, `transcript_alignment`, and frame-sampling artifact strategies.
- [x] Define multimodal output examples: cross-modal target ids, conflict deltas, and evidence citations.
- [x] Commit as `docs: add multimodal harness schema roadmap`.

### Task 6: Image-Native Output Comparator And Recipe

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Create: `backend/src/debug_agent/recipes/image_detection.py`
- Modify: `backend/src/debug_agent/recipes/registry.py`
- Modify: `backend/src/debug_agent/recipes/__init__.py`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/cases/test_comparator.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/recipes/test_registry.py`

- [x] Add `ImageRegionOutput` and `ImageDetectionOutput` with task-native `target_id`, region geometry, label, and confidence fields.
- [x] Add `parse_image_detection_output(raw_output: str)`.
- [x] Add `compare_image_detection_outputs(expected, predicted)` returning generic deltas such as `image:region:1 region_label_mismatch` and `missing_region`.
- [x] Add `judge_image_detection_output()` and route `task_type="image_detection"` runner parsing through `expected_output.regions`.
- [x] Add `ImageDetectionRecipe` with baseline replay, region schema check, and localization prompt check steps.
- [x] Keep OCR `AnswerSet`, `box_id`, and `student_answer` as compatibility-only paths.

### Task 7: Video-Native Output Comparator And Recipe

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Create: `backend/src/debug_agent/recipes/video_detection.py`
- Modify: `backend/src/debug_agent/recipes/registry.py`
- Modify: `backend/src/debug_agent/recipes/__init__.py`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/cases/test_comparator.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/recipes/test_registry.py`

- [x] Add `VideoSegmentOutput` and `VideoDetectionOutput` with task-native temporal target ids, time windows, labels, and confidence fields.
- [x] Add `parse_video_detection_output(raw_output: str)`.
- [x] Add `compare_video_detection_outputs(expected, predicted)` returning generic deltas such as `video:segment:1 segment_label_mismatch` and `missing_segment`.
- [x] Add `judge_video_detection_output()` and route `task_type="video_detection"` runner parsing through `expected_output.temporal_segments`.
- [x] Add `VideoDetectionRecipe` with baseline replay, temporal schema check, and temporal grounding check steps.
- [x] Keep video harness prompts free of OCR answer-box assumptions.

### Task 8: Multimodal-Native Conflict Comparator And Recipe

**Files:**
- Modify: `backend/src/debug_agent/cases/models.py`
- Modify: `backend/src/debug_agent/cases/comparator.py`
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Create: `backend/src/debug_agent/recipes/multimodal_detection.py`
- Modify: `backend/src/debug_agent/recipes/registry.py`
- Modify: `backend/src/debug_agent/recipes/__init__.py`
- Test: `backend/tests/cases/test_models.py`
- Test: `backend/tests/cases/test_comparator.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/recipes/test_registry.py`

- [x] Add `MultimodalConflictOutput` and `MultimodalDetectionOutput` for cross-modal conflicts.
- [x] Add `parse_multimodal_detection_output(raw_output: str)`.
- [x] Add `compare_multimodal_detection_outputs(expected, predicted)` returning generic deltas such as `multimodal:conflict:1 conflict_actual_mismatch` and `missing_conflict`.
- [x] Add `judge_multimodal_detection_output()` and route `task_type="multimodal_detection"` runner parsing through `expected_output.conflicts`.
- [x] Add `MultimodalDetectionRecipe` with cross-modal schema check, modality ablation check, and conflict grounding check steps.
- [x] Keep multimodal harness prompts centered on modality isolation and evidence grounding instead of OCR assumptions.

### Task 9: Frontend Native Delta Evidence Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] Add `JudgeDelta` frontend type for generic `target_id`, `expected`, `actual`, `reason`, and `metadata`.
- [x] Display task-native judge deltas in evidence detail for image, video, classification, and multimodal tasks.
- [x] Keep the delta section hidden for successful or legacy evidence without structured deltas.
- [x] Preserve existing generic artifact and legacy image artifact rendering.

### Task 10: Generic Expected Output Import Entry Point

**Files:**
- Modify: `backend/src/debug_agent/imports/csv_cases.py`
- Modify: `backend/src/debug_agent/imports/spreadsheet_rows.py`
- Test: `backend/tests/imports/test_csv_cases.py`
- Test: `backend/tests/imports/test_spreadsheet_rows.py`

- [x] Allow non-OCR task rows to omit `golden_answer_json` when `expected_output_json` is present.
- [x] Preserve `golden_answer_json` as required for `handwriting_ocr` rows.
- [x] Use empty `AnswerSet(answers=[])` only as a compatibility placeholder for task-native rows.
- [x] Keep existing CSV and spreadsheet OCR imports compatible.

## Multimodal Harness Schema Roadmap

### Image-Native Outputs

- `regions`: spatial targets with `target_id`, `x`, `y`, `width`, `height`, `unit`, and optional `label`.
- `objects`: detected entities with `target_id`, `name`, `attributes`, and optional region references.
- `attributes`: visual properties such as color, count, state, text, pose, relation, and uncertainty.
- `relations`: pairwise or group assertions such as `left_of`, `contains`, `overlaps`, `same_as`, or `missing`.
- Evidence strategy: original input snapshot, crop pyramid, zoomed candidate regions, contrast/rotation variants, and model self-localization prompts.

### Video-Native Outputs

- `temporal_segments`: time-window targets with `start_ms`, `end_ms`, `label`, and confidence.
- `keyframes`: selected frame targets with `timestamp_ms`, image artifact references, and frame-level observations.
- `events`: action or state-change assertions linked to temporal segments and keyframes.
- `transcript_alignment`: subtitle/audio/text spans aligned to frames or segments.
- Evidence strategy: fixed and adaptive frame sampling, before/after frame windows, segment thumbnails, temporal counterfactual prompts, and transcript/visual alignment checks.

### Multimodal Outputs

- Cross-modal target ids should include modality prefixes, such as `image:region:7`, `video:segment:3`, `text:span:12`, and `audio:span:4`.
- Conflict deltas should describe modality disagreement, for example `visual_text_conflict`, `audio_visual_conflict`, `temporal_grounding_mismatch`, or `schema_field_mismatch`.
- Evidence citations should link each delta to the exact request, output, artifact ids, region/segment ids, and scoring-standard clause.
- Harness strategy should isolate modality contribution through prompt ablations, frame/crop removal, transcript-only replay, image/video-only replay, and counterfactual expected-output checks.

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

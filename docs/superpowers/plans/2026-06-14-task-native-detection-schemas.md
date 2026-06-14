# Task Native Detection Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move non-OCR debug tasks toward task-native schemas while preserving OCR-compatible imports, storage, reports, and spreadsheet flows.

**Architecture:** Keep `AnswerSet` as the OCR adapter and introduce task-native output models beside it. Add focused parse/compare/judge paths for classification first, then route runner/judge behavior through task recipes so future visual detection and text/schema extraction can avoid OCR field names.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React/TypeScript/Vitest.

---

## Target Milestones

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
- [ ] Commit as `feat(core): add classification output comparator`.

### Task 2: Classification Judge Path

**Files:**
- Modify: `backend/src/debug_agent/judging/runner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/judging/test_runner.py`
- Test: `backend/tests/experiments/test_runner.py`

- [ ] Add `judge_classification_output()`.
- [ ] Route `task_type="classification"` runner parsing and judging through classification output models.
- [ ] Preserve OCR runner behavior for `handwriting_ocr`.
- [ ] Run focused judge and runner tests.
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

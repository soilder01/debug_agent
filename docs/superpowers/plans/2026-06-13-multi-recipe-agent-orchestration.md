# Multi Recipe Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development before production edits. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Debug Detection Agent from one OCR-first workflow into a multi-recipe orchestration core that can route generic debug tasks without OCR fallback.

**Architecture:** Keep the single durable worker as the enterprise execution boundary, but make its internal agent capabilities explicit and swappable by task type. Introduce a recipe registry, a generic classification recipe, and agent-role metadata so the main worker can coordinate Case Intake, Planning, Runner, Judge, Evidence, Report, and Writeback capabilities consistently.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy/SQLite, pytest, React/TypeScript/Vitest.

---

## Product Direction

The current system has one main durable debug worker and seven logical sub-agent capabilities implemented as modules:

- Case Intake Agent: imports JSONL/CSV/spreadsheet rows and stores debug cases.
- Experiment Planner/Recipe Agent: turns a case into replay and diagnosis steps.
- Model Runner Agent: calls the configured model and captures durable evidence.
- Judge/Comparator Agent: scores outputs and emits structured deltas.
- Evidence Artifact Agent: creates input/output/image artifact chains.
- Report/Root Cause Agent: infers root cause and builds writeback fields.
- Writeback/Operator Agent: syncs conclusions back to spreadsheet/operator views.

These are not separate deployed services yet. The next goal is to make their contracts explicit enough that the main worker can safely support multiple task types before any service split.

## Target Milestones

### Task 1: Recipe Registry Without OCR Fallback

**Files:**
- Create: `backend/src/debug_agent/recipes/registry.py`
- Modify: `backend/src/debug_agent/recipes/__init__.py`
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Test: `backend/tests/recipes/test_registry.py`
- Test: `backend/tests/experiments/test_planner.py`

- [x] Write a failing test that `recipe_for_task_type("unknown")` returns a generic default recipe instead of `HandwritingOcrRecipe`.
- [x] Write a failing test that planner routes `handwriting_ocr` to `HandwritingOcrRecipe` and `classification` to a non-OCR recipe.
- [x] Implement `RecipeRegistry` with explicit `handwriting_ocr` registration and a generic fallback recipe.
- [x] Update planner and runner imports to use `debug_agent.recipes.recipe_for_task_type`.
- [x] Run `python -m pytest backend/tests/recipes/test_registry.py backend/tests/experiments/test_planner.py -q`.
- [x] Commit as `feat(core): add task recipe registry`.

### Task 2: Classification Debug Recipe

**Files:**
- Create: `backend/src/debug_agent/recipes/classification.py`
- Modify: `backend/src/debug_agent/recipes/registry.py`
- Test: `backend/tests/recipes/test_classification.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] Write a failing test that a `classification` case plans `baseline_replay`, `label_schema_check`, and `counterfactual_prompt_check`.
- [x] Write a failing test that classification prompts mention labels/expected output but do not mention OCR boxes or handwriting regions.
- [x] Implement `ClassificationRecipe.plan_steps()` with small, bounded trial counts.
- [x] Implement `ClassificationRecipe.build_step_prompt()` with schema-focused instructions.
- [x] Register `classification` in `RecipeRegistry`.
- [x] Run `python -m pytest backend/tests/recipes/test_classification.py backend/tests/experiments/test_runner.py -q`.
- [x] Commit as `feat(core): add classification debug recipe`.

### Task 3: Agent Role Metadata

**Files:**
- Create: `backend/src/debug_agent/orchestration/roles.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/orchestration/test_roles.py`
- Test: `backend/tests/experiments/test_runner.py`

- [x] Write a failing test that lists the seven logical agent roles with stable ids and responsibilities.
- [x] Write a failing test that each evidence record includes `agent_role="model_runner"` in request metadata.
- [x] Implement `AgentRole` and `logical_agent_roles()`.
- [x] Add role metadata to evidence request summaries without changing existing keys.
- [x] Run `python -m pytest backend/tests/orchestration/test_roles.py backend/tests/experiments/test_runner.py -q`.
- [x] Commit as `feat(core): expose logical agent roles`.

### Task 4: Frontend Agent Topology Panel

**Files:**
- Create: `frontend/src/orchestration/AgentTopologyPanel.tsx`
- Create: `frontend/src/orchestration/AgentTopologyPanel.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [x] Write a failing UI test that renders seven logical agent capabilities under `Agent Topology`.
- [x] Implement a static topology panel matching backend role ids and responsibilities.
- [x] Mount the panel near operational monitoring.
- [x] Run `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/orchestration/AgentTopologyPanel.test.tsx src/app/App.test.tsx`.
- [x] Commit as `feat(frontend): show agent topology`.

### Task 5: Full Verification And Roadmap Refresh

**Files:**
- Modify: `docs/superpowers/plans/2026-06-13-multi-recipe-agent-orchestration.md`
- Modify: `docs/superpowers/plans/2026-06-13-general-debug-detection-core.md`

- [x] Run `.\scripts\verify.ps1`.
- [x] Run `git diff --check`.
- [x] Run `git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'`.
- [x] Update both plan files with completed checkpoints and remaining risks.
- [ ] Commit as `docs: refresh multi agent roadmap`.

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

- Added explicit recipe registry with OCR, classification, and generic fallback routing.
- Added `ClassificationRecipe` with label/schema-focused replay steps and prompt augmentation.
- Added backend logical agent roles for seven internal sub-agent capabilities.
- Added frontend Agent Topology panel so operators can see the current orchestration shape.

## Current Agent Topology

- `case_intake`: import and normalize cases.
- `experiment_planner`: route task types and build experiment plans.
- `model_runner`: execute model calls and capture durable evidence.
- `judge_comparator`: score outputs and emit deltas.
- `evidence_artifact`: create input/output/image artifacts.
- `report_root_cause`: infer root cause and produce reports.
- `writeback_operator`: write conclusions back with audit records.

## Remaining Risks

- Agent roles are still logical modules inside one durable worker, not separately deployed services.
- Frontend topology is static; later work should fetch backend role metadata through an API to avoid drift.
- Classification recipe still uses OCR-compatible `AnswerSet` input/output shape until task-native schemas are introduced.

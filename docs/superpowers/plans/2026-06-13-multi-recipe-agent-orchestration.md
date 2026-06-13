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

- [ ] Write a failing test that `recipe_for_task_type("unknown")` returns a generic default recipe instead of `HandwritingOcrRecipe`.
- [ ] Write a failing test that planner routes `handwriting_ocr` to `HandwritingOcrRecipe` and `classification` to a non-OCR recipe.
- [ ] Implement `RecipeRegistry` with explicit `handwriting_ocr` registration and a generic fallback recipe.
- [ ] Update planner and runner imports to use `debug_agent.recipes.recipe_for_task_type`.
- [ ] Run `python -m pytest backend/tests/recipes/test_registry.py backend/tests/experiments/test_planner.py -q`.
- [ ] Commit as `feat(core): add task recipe registry`.

### Task 2: Classification Debug Recipe

**Files:**
- Create: `backend/src/debug_agent/recipes/classification.py`
- Modify: `backend/src/debug_agent/recipes/registry.py`
- Test: `backend/tests/recipes/test_classification.py`
- Test: `backend/tests/experiments/test_runner.py`

- [ ] Write a failing test that a `classification` case plans `baseline_replay`, `label_schema_check`, and `counterfactual_prompt_check`.
- [ ] Write a failing test that classification prompts mention labels/expected output but do not mention OCR boxes or handwriting regions.
- [ ] Implement `ClassificationRecipe.plan_steps()` with small, bounded trial counts.
- [ ] Implement `ClassificationRecipe.build_step_prompt()` with schema-focused instructions.
- [ ] Register `classification` in `RecipeRegistry`.
- [ ] Run `python -m pytest backend/tests/recipes/test_classification.py backend/tests/experiments/test_runner.py -q`.
- [ ] Commit as `feat(core): add classification debug recipe`.

### Task 3: Agent Role Metadata

**Files:**
- Create: `backend/src/debug_agent/orchestration/roles.py`
- Modify: `backend/src/debug_agent/experiments/runner.py`
- Modify: `backend/src/debug_agent/reports/generator.py`
- Test: `backend/tests/orchestration/test_roles.py`
- Test: `backend/tests/experiments/test_runner.py`

- [ ] Write a failing test that lists the seven logical agent roles with stable ids and responsibilities.
- [ ] Write a failing test that each evidence record includes `agent_role="model_runner"` in request metadata.
- [ ] Implement `AgentRole` and `logical_agent_roles()`.
- [ ] Add role metadata to evidence request summaries without changing existing keys.
- [ ] Run `python -m pytest backend/tests/orchestration/test_roles.py backend/tests/experiments/test_runner.py -q`.
- [ ] Commit as `feat(core): expose logical agent roles`.

### Task 4: Frontend Agent Topology Panel

**Files:**
- Create: `frontend/src/orchestration/AgentTopologyPanel.tsx`
- Create: `frontend/src/orchestration/AgentTopologyPanel.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] Write a failing UI test that renders seven logical agent capabilities under `Agent Topology`.
- [ ] Implement a static topology panel matching backend role ids and responsibilities.
- [ ] Mount the panel near operational monitoring.
- [ ] Run `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/orchestration/AgentTopologyPanel.test.tsx src/app/App.test.tsx`.
- [ ] Commit as `feat(frontend): show agent topology`.

### Task 5: Full Verification And Roadmap Refresh

**Files:**
- Modify: `docs/superpowers/plans/2026-06-13-multi-recipe-agent-orchestration.md`
- Modify: `docs/superpowers/plans/2026-06-13-general-debug-detection-core.md`

- [ ] Run `.\scripts\verify.ps1`.
- [ ] Run `git diff --check`.
- [ ] Run `git ls-files -co --exclude-standard | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'`.
- [ ] Update both plan files with completed checkpoints and remaining risks.
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

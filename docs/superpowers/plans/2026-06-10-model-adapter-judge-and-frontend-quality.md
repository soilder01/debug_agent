# Model Adapter Judge And Frontend Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a testable model replay abstraction, a deterministic judge runner, and frontend quality gates without making live Seed model calls part of unit tests.

**Architecture:** Backend model access is isolated behind adapter interfaces: fake adapters are used by unit tests, Ark/Seed adapters read configuration from environment variables and are only used by explicit integration jobs. Judge logic consumes normalized `AnswerSet` data and produces explainable pass/fail reasons. Frontend quality gates add Vitest component tests and ESLint configuration so the review UI can evolve safely.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, httpx, FastAPI, React 18, TypeScript, Vitest, Testing Library, ESLint.

---

## Scope

This plan intentionally avoids live API calls in automated tests. Real Seed 2.0 Lite/Pro calls are introduced as manually triggered integration behavior after deterministic adapters and judging contracts are stable.

## Files

```text
backend/src/debug_agent/settings.py
backend/src/debug_agent/models/__init__.py
backend/src/debug_agent/models/adapters.py
backend/src/debug_agent/models/fake.py
backend/src/debug_agent/models/ark.py
backend/src/debug_agent/judging/__init__.py
backend/src/debug_agent/judging/runner.py
backend/tests/models/test_fake_adapter.py
backend/tests/models/test_ark_adapter.py
backend/tests/judging/test_runner.py
frontend/src/app/App.test.tsx
frontend/src/test/setup.ts
frontend/eslint.config.js
frontend/vitest.config.ts
frontend/package.json
scripts/verify.ps1
docs/model-configuration.md
```

## Task 1: Backend Settings

**Files:**
- Create: `backend/src/debug_agent/settings.py`
- Test: `backend/tests/models/test_ark_adapter.py`

- [ ] **Step 1: Write settings test**

```python
from debug_agent.settings import ArkSettings


def test_ark_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("ARK_API_KEY", "secret-value")
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.example/api/v3")
    monkeypatch.setenv("ARK_SEED2_LITE_MODEL_ID", "lite-model")
    monkeypatch.setenv("ARK_SEED2_PRO_MODEL_ID", "pro-model")

    settings = ArkSettings.from_env()

    assert settings.api_key.get_secret_value() == "secret-value"
    assert settings.base_url == "https://ark.example/api/v3"
    assert settings.seed2_lite_model_id == "lite-model"
    assert settings.seed2_pro_model_id == "pro-model"
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/models/test_ark_adapter.py -q`
Expected: fails because `debug_agent.settings` does not exist.

- [ ] **Step 3: Implement settings**

```python
import os

from pydantic import BaseModel, SecretStr


class ArkSettings(BaseModel):
    api_key: SecretStr
    base_url: str = "https://ark-cn-beijing.bytedance.net/api/v3"
    content_tasks_url: str = "https://ark-cn-beijing.bytedance.net/api/v3/contents/generations/tasks"
    seed2_lite_model_id: str = "ep-20260609151048-sbfnk"
    seed2_pro_model_id: str = "ep-20260609191630-7gkjm"

    @classmethod
    def from_env(cls) -> "ArkSettings":
        api_key = os.environ.get("ARK_API_KEY", "")
        if not api_key:
            raise RuntimeError("ARK_API_KEY is required for live Ark model calls")
        return cls(
            api_key=SecretStr(api_key),
            base_url=os.environ.get("ARK_BASE_URL", cls.model_fields["base_url"].default),
            content_tasks_url=os.environ.get(
                "ARK_CONTENT_TASKS_URL", cls.model_fields["content_tasks_url"].default
            ),
            seed2_lite_model_id=os.environ.get(
                "ARK_SEED2_LITE_MODEL_ID", cls.model_fields["seed2_lite_model_id"].default
            ),
            seed2_pro_model_id=os.environ.get(
                "ARK_SEED2_PRO_MODEL_ID", cls.model_fields["seed2_pro_model_id"].default
            ),
        )
```

- [ ] **Step 4: Verify settings**

Run: `cd backend && python -m pytest tests/models/test_ark_adapter.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/settings.py backend/tests/models/test_ark_adapter.py
git commit -m "feat: add Ark settings contract"
```

## Task 2: Model Adapter Interfaces

**Files:**
- Create: `backend/src/debug_agent/models/__init__.py`
- Create: `backend/src/debug_agent/models/adapters.py`
- Create: `backend/src/debug_agent/models/fake.py`
- Test: `backend/tests/models/test_fake_adapter.py`

- [ ] **Step 1: Write fake adapter test**

```python
import pytest

from debug_agent.models.fake import FakeModelAdapter


@pytest.mark.asyncio
async def test_fake_model_adapter_returns_configured_outputs() -> None:
    adapter = FakeModelAdapter(outputs=["first", "second"])

    first = await adapter.generate(prompt="prompt", image_uri="")
    second = await adapter.generate(prompt="prompt", image_uri="")

    assert first.raw_output == "first"
    assert first.model_name == "fake"
    assert second.raw_output == "second"
    assert second.trial == 1
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/models/test_fake_adapter.py -q`
Expected: fails because model adapter modules do not exist.

- [ ] **Step 3: Implement adapter contract**

```python
from typing import Protocol

from pydantic import BaseModel


class ModelResponse(BaseModel):
    model_name: str
    trial: int
    raw_output: str


class ModelAdapter(Protocol):
    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        """Generate a model response for one prompt/image condition."""
```

- [ ] **Step 4: Implement fake adapter**

```python
from debug_agent.models.adapters import ModelResponse


class FakeModelAdapter:
    def __init__(self, outputs: list[str], model_name: str = "fake") -> None:
        self._outputs = outputs
        self._model_name = model_name
        self._cursor = 0

    async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
        del prompt, image_uri
        if not self._outputs:
            raise RuntimeError("FakeModelAdapter requires at least one output")
        trial = self._cursor
        output = self._outputs[min(self._cursor, len(self._outputs) - 1)]
        self._cursor += 1
        return ModelResponse(model_name=self._model_name, trial=trial, raw_output=output)
```

- [ ] **Step 5: Verify fake adapter**

Run: `cd backend && python -m pytest tests/models/test_fake_adapter.py -q`
Expected: passes.

- [ ] **Step 6: Commit**

Run:
```bash
git add backend/src/debug_agent/models backend/tests/models/test_fake_adapter.py
git commit -m "feat: add model adapter contract and fake adapter"
```

## Task 3: Ark Adapter Request Builder

**Files:**
- Create: `backend/src/debug_agent/models/ark.py`
- Modify: `backend/tests/models/test_ark_adapter.py`

- [ ] **Step 1: Add request-building test**

Append to `backend/tests/models/test_ark_adapter.py`:

```python
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.settings import ArkSettings


def test_ark_adapter_builds_request_without_exposing_secret() -> None:
    settings = ArkSettings(
        api_key="secret-value",
        base_url="https://ark.example/api/v3",
        content_tasks_url="https://ark.example/api/v3/contents/generations/tasks",
        seed2_lite_model_id="lite-model",
        seed2_pro_model_id="pro-model",
    )
    adapter = ArkModelAdapter(settings=settings, model_id=settings.seed2_lite_model_id)

    request = adapter.build_request(prompt="hello", image_uri="tos://image")

    assert request.url == "https://ark.example/api/v3/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-value"
    assert request.json_body["model"] == "lite-model"
    assert "secret-value" not in repr(request)
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/models/test_ark_adapter.py -q`
Expected: fails because `debug_agent.models.ark` does not exist.

- [ ] **Step 3: Implement Ark request builder**

```python
from pydantic import BaseModel, Field

from debug_agent.settings import ArkSettings


class ArkRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(repr=False)
    json_body: dict[str, object]


class ArkModelAdapter:
    def __init__(self, settings: ArkSettings, model_id: str) -> None:
        self._settings = settings
        self._model_id = model_id

    def build_request(self, prompt: str, image_uri: str) -> ArkRequest:
        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        if image_uri:
            content.append({"type": "image_url", "image_url": {"url": image_uri}})
        return ArkRequest(
            url=f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key.get_secret_value()}"},
            json_body={
                "model": self._model_id,
                "messages": [{"role": "user", "content": content}],
            },
        )
```

- [ ] **Step 4: Verify Ark adapter**

Run: `cd backend && python -m pytest tests/models/test_ark_adapter.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/models/ark.py backend/tests/models/test_ark_adapter.py
git commit -m "feat: add Ark model request builder"
```

## Task 4: Judge Runner

**Files:**
- Create: `backend/src/debug_agent/judging/__init__.py`
- Create: `backend/src/debug_agent/judging/runner.py`
- Test: `backend/tests/judging/test_runner.py`

- [ ] **Step 1: Write judge tests**

```python
from debug_agent.cases.models import AnswerSet
from debug_agent.judging.runner import judge_answer


def test_judge_answer_passes_exact_match() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})

    result = judge_answer(expected, predicted)

    assert result.score == 1
    assert result.reasons == []


def test_judge_answer_explains_mismatch() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低昷烘干"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低温烘干"}]})

    result = judge_answer(expected, predicted)

    assert result.score == 0
    assert result.reasons == ["box 1 student_answer_mismatch"]
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/judging/test_runner.py -q`
Expected: fails because judge runner does not exist.

- [ ] **Step 3: Implement judge runner**

```python
from pydantic import BaseModel

from debug_agent.cases.comparator import compare_answer_sets
from debug_agent.cases.models import AnswerSet


class JudgeResult(BaseModel):
    score: int
    reasons: list[str]


def judge_answer(expected: AnswerSet, predicted: AnswerSet) -> JudgeResult:
    diff = compare_answer_sets(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[])
    return JudgeResult(
        score=0,
        reasons=[f"box {delta.box_id} {delta.reason}" for delta in diff.deltas],
    )
```

- [ ] **Step 4: Verify judge runner**

Run: `cd backend && python -m pytest tests/judging/test_runner.py -q`
Expected: passes.

- [ ] **Step 5: Commit**

Run:
```bash
git add backend/src/debug_agent/judging backend/tests/judging/test_runner.py
git commit -m "feat: add deterministic judge runner"
```

## Task 5: Frontend Test And Lint Gate

**Files:**
- Create: `frontend/src/app/App.test.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/eslint.config.js`
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json`
- Modify: `scripts/verify.ps1`

- [ ] **Step 1: Add frontend testing dependencies**

Update `frontend/package.json` devDependencies with:

```json
"@testing-library/jest-dom": "^6.6.3",
"@testing-library/react": "^16.1.0",
"@testing-library/user-event": "^14.5.2",
"@eslint/js": "^9.17.0",
"typescript-eslint": "^8.18.0",
"globals": "^15.14.0",
"jsdom": "^25.0.1"
```

- [ ] **Step 2: Add Vitest config**

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"]
  }
});
```

- [ ] **Step 3: Add test setup**

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Add App test**

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("runs single-case debug and renders report", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          case_id: "handwrite233",
          status: "needs_human_review",
          observed_failure: { type: "erasure_revision_failure", summary: "", affected_box_ids: [1] },
          planned_experiments: ["baseline_replay"],
          root_cause: { label: "erasure_revision_failure", confidence: "medium", evidence_summary: "evidence" },
          suggested_sheet_fields: { "debug1状态": "待人工确认" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Run single-case debug" }));

    expect(await screen.findByText("样本 ID：handwrite233")).toBeInTheDocument();
    expect(screen.getByText("baseline_replay")).toBeInTheDocument();
    expect(screen.getByText("erasure_revision_failure")).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Add ESLint config**

```javascript
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser
    }
  }
);
```

- [ ] **Step 6: Update verification script**

Ensure `scripts/verify.ps1 -Target all` also runs:

```powershell
Run-Step "frontend tests" "npx --yes pnpm@9.15.4 test -- --run" "frontend"
Run-Step "frontend lint" "npx --yes pnpm@9.15.4 lint" "frontend"
```

- [ ] **Step 7: Run frontend gates**

Run: `cd frontend && npx --yes pnpm@9.15.4 install && npx --yes pnpm@9.15.4 test -- --run && npx --yes pnpm@9.15.4 lint && npx --yes pnpm@9.15.4 typecheck`
Expected: all pass.

- [ ] **Step 8: Commit**

Run:
```bash
git add frontend scripts/verify.ps1
git commit -m "test: add frontend quality gates"
```

## Task 6: Full Verification

**Files:**
- Modify: `docs/model-configuration.md`

- [ ] **Step 1: Document integration-test policy**

Append:

```markdown
## Integration Test Policy

Live Seed model calls are never part of unit tests or default CI. They must be run through explicitly named integration commands after confirming `ARK_API_KEY` is available in the local environment.
```

- [ ] **Step 2: Run full verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`
Expected: backend tests, frontend tests, backend lint, frontend lint, backend typecheck, and frontend typecheck pass.

- [ ] **Step 3: Scan for leaked secrets**

Run: `git grep -n "ark-[0-9a-f]" -- . ':!docs/superpowers/plans/*'`
Expected: no matches.

- [ ] **Step 4: Commit docs**

Run:
```bash
git add docs/model-configuration.md
git commit -m "docs: document live model integration policy"
```

---

## Self-Review

Spec coverage:
- Seed model configuration is represented through safe env-based settings.
- Unit tests remain deterministic and do not call live APIs.
- Judge runner explains pass/fail reasons.
- Frontend now has test, lint, and typecheck gates.

Placeholder scan:
- No placeholder or open-ended implementation steps are present.

Type consistency:
- `ArkSettings`, `ArkModelAdapter`, `ModelResponse`, and `JudgeResult` are named consistently across tests and implementation.

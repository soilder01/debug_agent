# Ark Generate Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement `ArkModelAdapter.generate()` behind an injectable transport so tests remain offline while live model execution becomes possible.

**Architecture:** Add an `ArkTransport` protocol and a stdlib `UrllibArkTransport` implementation. `ArkModelAdapter.generate()` builds the request, posts it through the transport, parses OpenAI-compatible `choices[0].message.content`, and returns `ModelResponse`.

**Tech Stack:** Python 3.11, stdlib `urllib`, Pydantic v2, pytest-asyncio, mypy.

---

## File Structure

- Modify `backend/src/debug_agent/models/ark.py`: add transport protocol, default transport, response parsing, and generate implementation.
- Modify `backend/tests/models/test_ark_adapter.py`: add offline tests for generate success and malformed response rejection.
- Create `docs/superpowers/plans/2026-06-11-ark-generate-transport.md`: this plan.

## Task 1: Ark Generate With Injected Transport

**Files:**
- Modify: `backend/src/debug_agent/models/ark.py`
- Modify: `backend/tests/models/test_ark_adapter.py`

- [x] **Step 1: Write failing tests**

Add async tests using a fake transport to verify `generate()` returns raw model content and rejects malformed responses.

- [x] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/models/test_ark_adapter.py -q
```

Expected: FAIL because `generate()` raises `NotImplementedError`.

- [x] **Step 3: Implement transport and parser**

Implement `ArkTransport`, `UrllibArkTransport`, `ArkModelAdapter.generate()`, and a private parser.

- [x] **Step 4: Run focused tests and mypy**

Run:

```powershell
python -m pytest tests/models/test_ark_adapter.py -q
python -m mypy src
```

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/models/ark.py`
- Modify: `backend/tests/models/test_ark_adapter.py`
- Create: `docs/superpowers/plans/2026-06-11-ark-generate-transport.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: all tests, lint, and typecheck pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan edited files for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```powershell
git add backend/src/debug_agent/models/ark.py backend/tests/models/test_ark_adapter.py docs/superpowers/plans/2026-06-11-ark-generate-transport.md
git commit -m "feat(models): implement ark generate transport"
```

Expected: one commit containing only Phase 31 changes.

## Self-Review

- Spec coverage: The plan enables live-capable Ark generation while tests remain offline through injected transport.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: `generate()` returns the existing `ModelResponse`.

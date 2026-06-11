# Retry Recommendation Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add human-readable retry guidance to job status while preserving the machine-readable recommendation code.

**Architecture:** The backend owns recommendation semantics and returns a structured detail object with `code`, `label`, `action`, and `severity`. The frontend renders this detail in the job status panel with a fallback to the existing code for older responses.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Recommendation Detail

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_status.py`

- [x] **Step 1: Add failing API assertions**

Add assertions that `GET /jobs/{job_id}` includes:

```python
assert body["retry_recommendation_detail"] == {
    "code": "no_retry_needed",
    "label": "无需重试",
    "action": "任务已完成，直接查看证据链和结论。",
    "severity": "info",
}
```

- [x] **Step 2: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_status.py -q`
Expected: FAIL because `retry_recommendation_detail` is missing.

- [x] **Step 3: Implement backend detail mapping**

Add a `RetryRecommendationDetail` Pydantic model and a `retry_recommendation_detail()` service method that maps each code to label/action/severity.

- [x] **Step 4: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_status.py -q`
Expected: PASS.

### Task 2: Frontend Guidance Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/jobs/JobStatusPanel.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Add a mock `retry_recommendation_detail` and assert:

```typescript
expect(screen.getByText("重试建议：无需重试")).toBeInTheDocument();
expect(screen.getByText("建议动作：任务已完成，直接查看证据链和结论。")).toBeInTheDocument();
```

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the panel still renders the raw code.

- [x] **Step 3: Implement frontend rendering**

Extend TypeScript types and render the detail label/action with fallback to the raw code.

- [x] **Step 4: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 3: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-retry-recommendation-guidance.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add backend/src/debug_agent/jobs/service.py backend/src/debug_agent/api/routes.py backend/tests/api/test_job_status.py frontend/src/api/client.ts frontend/src/jobs/JobStatusPanel.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-retry-recommendation-guidance.md
git commit -m "feat(jobs): add retry guidance"
```

# Crop Preview Links Implementation Plan

> **For agentic workers:** Use TDD. Crop preview UX should still be useful when thumbnails fail to load.

**Goal:** Give operators direct links to open generated crop previews and clearly show when no preview URL is available.

**Architecture:** Enhance `EvidenceDetail` rendering only: when `preview_image_url` exists, show an image and an open link; otherwise render an explicit no-preview message.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Evidence Detail Links

**Files:**
- Modify: `frontend/src/evidence/EvidenceDetail.tsx`
- Test: `frontend/src/evidence/EvidenceDetail.test.tsx`

- [x] **Step 1: Add failing preview link test**

Assert artifacts with `preview_image_url` render an open link and artifacts without one render `预览图：无`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx`
Expected: FAIL because links and no-preview copy do not exist.

- [x] **Step 3: Implement preview link rendering**

Render an anchor for preview URLs and a visible no-preview fallback.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/evidence/EvidenceDetail.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(evidence): add crop preview links`.

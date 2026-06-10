# Handwriting OCR Debug Agent

Enterprise-grade agent harness for debugging handwriting OCR badcases.

## Goals

- Reproduce model failures with controlled experiments.
- Explain root causes using evidence rather than speculation.
- Reduce manual debug effort while preserving human review.
- Provide a frontend for case inspection, experiment tracking, and report approval.

## Local Commands

- `make test`: run backend unit tests.
- `make lint`: run backend and frontend lint checks.
- `make typecheck`: run Python and TypeScript type checks.
- `make dev`: start local backend and frontend services.

## Model Configuration

The project reads model credentials from environment variables. Keep real secrets in your shell or local `.env` file only. Use `.env.example` as the committed template.

## Quality Bar

This repository is built through small tested slices. A feature is complete only when tests, docs, and local verification pass.
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

The project reads model credentials from environment variables and automatically loads a local `.env` file. Keep real secrets in your shell or local `.env` file only. Use `.env.example` as the committed template, then replace the `ARK_API_KEY` placeholder locally.

`.env.example` is configured for `DEBUG_AGENT_MODEL_PROVIDER=ark-seed2-lite` with the Seed 2.0 Lite endpoint/model id. Default verification still does not call live models because live tests require `DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS=1`. To intentionally run the gated Ark integration test, set a real `ARK_API_KEY` and run:

```powershell
python -m pytest tests/integration/test_live_ark_adapter.py -q
```

## Lark Spreadsheet Configuration

The backend can sync rows from Lark spreadsheets and write report fields back through local `lark-cli` auth. Copy `.env.example` to `.env`, keep secrets out of git, and make sure `lark-cli` is authenticated as a user that can read/write the target spreadsheet.

The committed Lark fixture is:

```env
LARK_SPREADSHEET_URL=https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX
LARK_SHEET_ID=qJAomX
LARK_CLI_TIMEOUT_SECONDS=60
DEBUG_AGENT_REPORT_BASE_URL=http://localhost:8000
DEBUG_AGENT_AUTO_WRITEBACK_ENABLED=0
```

Current connectivity check result: `workbook-info` succeeds for this spreadsheet, and `qJAomX` maps to `Sheet9`. The sampled ranges `A1:AC40` and `A1:E394` currently read as empty values, so this fixture verifies URL parsing, auth, and transport connectivity rather than sample import content.

Automatic report writeback is intentionally disabled by default. With `DEBUG_AGENT_AUTO_WRITEBACK_ENABLED=0`, the worker runs jobs and persists reports/evidence, but it does not update Lark rows automatically. Manual writeback through `POST /jobs/{job_id}/spreadsheet-writeback` still works when a writeback client is configured.

To enable automatic writeback after validating permissions and target columns, set:

```env
DEBUG_AGENT_AUTO_WRITEBACK_ENABLED=1
```

Worker status exposes both `auto_writeback_enabled` and `completion_hook_enabled`. A job-level writeback audit is available from `GET /jobs/{job_id}/spreadsheet-writeback/audit` and is summarized in `GET /jobs` / `GET /jobs/{job_id}` as `spreadsheet_writeback_audit`.

## Quality Bar

This repository is built through small tested slices. A feature is complete only when tests, docs, and local verification pass.

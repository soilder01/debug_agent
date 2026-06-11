# Model Configuration

The default live model family is configured through environment variables. Do not commit real API keys.
Copy `.env.example` to `.env`, replace `ARK_API_KEY`, and the backend settings loader will read `.env` automatically.

## Environment Variables

- `ARK_API_KEY`: local secret for Ark API access. `.env.example` contains only a placeholder that must be replaced locally.
- `ARK_BASE_URL`: base URL for chat/model replay APIs.
- `ARK_CONTENT_TASKS_URL`: URL for content generation task APIs.
- `ARK_SEED2_LITE_MODEL_ID`: default lite model id for cost-aware repeated debug experiments.
- `ARK_SEED2_PRO_MODEL_ID`: optional stronger model id for escalation experiments.
- `DEBUG_AGENT_MODEL_PROVIDER`: runtime model provider. Supported values are `fake`, `ark-seed2-lite`, and `ark-seed2-pro`. `.env.example` uses `ark-seed2-lite` so the copied local `.env` is live-model ready after inserting a real key.
- `DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS`: set to `1` only when intentionally running live Ark integration tests.

## Security Rules

- Store real keys only in local shell environment variables or a local `.env` file.
- Never print keys in logs, reports, frontend payloads, or test fixtures.
- Unit tests must use deterministic fake adapters and must not require live API access.
- Live model calls belong in integration tests or manually approved debug jobs.

## Integration Test Policy

Live Seed model calls are never part of unit tests or default CI. They must be run through explicitly named integration commands after confirming `ARK_API_KEY` is available in the local environment.

Default verification still keeps live integration tests gated by `DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS=0`, so it never calls the live model unless that flag is explicitly set to `1`.

To intentionally run the live Ark adapter test locally:

```powershell
$env:ARK_API_KEY="<local-secret>"
$env:DEBUG_AGENT_MODEL_PROVIDER="ark-seed2-lite"
$env:DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS="1"
python -m pytest tests/integration/test_live_ark_adapter.py -q
```

Do not paste real keys into committed files, test fixtures, logs, screenshots, or frontend payloads.

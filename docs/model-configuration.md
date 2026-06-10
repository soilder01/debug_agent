# Model Configuration

The default live model family is configured through environment variables. Do not commit real API keys.

## Environment Variables

- `ARK_API_KEY`: local secret for Ark API access.
- `ARK_BASE_URL`: base URL for chat/model replay APIs.
- `ARK_CONTENT_TASKS_URL`: URL for content generation task APIs.
- `ARK_SEED2_LITE_MODEL_ID`: default lite model id for cost-aware repeated debug experiments.
- `ARK_SEED2_PRO_MODEL_ID`: optional stronger model id for escalation experiments.

## Security Rules

- Store real keys only in local shell environment variables or a local `.env` file.
- Never print keys in logs, reports, frontend payloads, or test fixtures.
- Unit tests must use deterministic fake adapters and must not require live API access.
- Live model calls belong in integration tests or manually approved debug jobs.

## Integration Test Policy

Live Seed model calls are never part of unit tests or default CI. They must be run through explicitly named integration commands after confirming `ARK_API_KEY` is available in the local environment.

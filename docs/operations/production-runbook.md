# Debug Agent Production Operations Runbook

## Scope

This runbook covers production-candidate operation for the Debug Agent backend, worker, artifacts, Lark connector, Knowledge/Chat/RAG expansion, XiaoD entrypoints, and operational exports.

## Required Environment

- `DEBUG_AGENT_ENVIRONMENT`: `local`, `pilot`, or production-candidate environment name.
- `DEBUG_AGENT_DATABASE_URL`: persistent database URL. SQLite is acceptable for local and short dogfood runs; production candidates should use a managed persistent database with backups.
- `DEBUG_AGENT_IMAGE_ARTIFACT_DIR`: writable artifact root for run outputs and generated assets.
- `DEBUG_AGENT_REPORT_BASE_URL`: operator-accessible backend base URL used in reports and writeback links.
- `DEBUG_AGENT_DOCKER_REPORT_BASE_URL`: Docker deployment public entry URL, default `http://localhost:8080`; compose maps it into `DEBUG_AGENT_REPORT_BASE_URL`.
- `DEBUG_AGENT_FRONTEND_PORT`: host port for the nginx frontend entry, default `8080`.
- `DEBUG_AGENT_QUEUE_MAX_CONCURRENCY`: worker concurrency.
- `DEBUG_AGENT_RETRY_MAX_ATTEMPTS`: retry budget per job.
- `DEBUG_AGENT_STALE_RUNNING_JOB_SECONDS`: stale running-job recovery window.
- `DEBUG_AGENT_ARTIFACT_RETENTION_DAYS`: artifact retention policy used by the dry-run retention endpoint.
- `DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR`: recommended `true` for production candidates.
- `DEBUG_AGENT_USAGE_BUDGET_UNITS` and `DEBUG_AGENT_ENFORCE_USAGE_BUDGET`: recommended for live model usage.
- `LARK_SPREADSHEET_URL`, `LARK_SHEET_ID`: required for Lark spreadsheet dogfood and writeback.
- `LARK_EVENT_MODE`: keep `long_connection` for XiaoD. Webhook is retained only as a legacy diagnostic path and is not a product acceptance path.
- `LARK_CLI_IDENTITY`: use `bot` for XiaoD.
- `LARK_CLI_PROFILE`: use `xiaoD` for XiaoD.
- `LARK_APP_ID` and `LARK_APP_SECRET`: required only when starting the Docker `lark-bot-consumer` profile with SDK long connection.
- `LARK_BOT_VERIFICATION_TOKEN` and `LARK_BOT_ENCRYPT_KEY`: not required for XiaoD long connection. Leave empty unless deliberately testing the legacy webhook parser.

## Docker Deployment

The Docker deployment is the preferred local production-candidate path. It builds images once and starts stable runtime containers instead of installing Python and Node dependencies during every start.

Services:

- `backend`: FastAPI API service, exposes host port `8000` for operator diagnostics.
- `worker`: async DebugJob worker, uses the same backend image and the same persistent artifact volume.
- `frontend`: nginx service, exposes host port `DEBUG_AGENT_FRONTEND_PORT` and serves the compiled React app.
- `lark-bot-consumer`: optional `lark` profile service for XiaoD long-connection events and card action handling.

Persistent volumes:

- `backend_artifacts`: SQLite database, RAG vector index, DebugLesson history, run artifacts, report artifacts, media downloads, and generated exports.
- `lark_cli_data`: `lark-cli` profile data for the optional XiaoD consumer.
- `lark_consumer_state`: persistent event dedup state for the optional XiaoD consumer.

Start the base deployment:

```powershell
docker compose up -d --build backend worker frontend
docker compose ps
curl.exe http://localhost:8080/health
curl.exe http://localhost:8080/api/assistant/knowledge/status
curl.exe http://localhost:8000/api/operations/readiness
```

Expected result:

- `backend` is `healthy`.
- `frontend` is `healthy`.
- `/health` returns `{"status":"ok","service":"debug-agent-backend"}` through nginx.
- `/api/assistant/knowledge/status` reports the SQLite vector store and non-zero document/chunk counts.
- `/api/operations/readiness` may show warnings for real secrets, public URL, or Feishu setup; those warnings are not Docker boot failures.

Start XiaoD only after the Feishu app credentials and bot permissions are ready:

```powershell
docker compose --profile lark up -d --build lark-bot-consumer
docker compose logs -f lark-bot-consumer
```

Do not use `docker compose down -v` during normal restarts. That deletes `backend_artifacts` and therefore removes the SQLite job state, RAG vector index, DebugLesson history, and generated reports.

## Startup Checks

1. Start the backend and worker using the deployment supervisor. For a local production-candidate backend, use `powershell -File scripts/start-production.ps1`.
2. Open `/api/operations/readiness`.
3. Resolve every `critical` check before allowing operator traffic.
4. Review every `warning` check before production-candidate rollout.
5. Open `/api/observability/summary` and confirm queue, evidence, usage, writeback, and health sections are visible.
6. Open `/api/performance/summary` and confirm API timing events are being recorded.
7. Open `/api/operations/artifact-retention` and confirm artifact growth is visible and cleanup candidates are expected.
8. Open `/api/operations/pilot-gate` before pilot rollout and resolve every `failed` check.

For automated preflight, run:

```powershell
python scripts/production_preflight.py --base-url http://127.0.0.1:8000 --output-json dogfood-output/production-preflight.json
```

The preflight exits non-zero on `failed` or `warning` status by default. Add `--allow-warning` only for explicitly approved dogfood runs.

Use `docs/operations/pilot-validation-template.md` to record the run, thresholds, exported evidence, decision, and approver for any real pilot validation.

To collect the evidence files and generate the Markdown record automatically, run:

```powershell
python scripts/pilot_validation_record.py --base-url http://127.0.0.1:8000 --output-dir dogfood-output/pilot-validation --include-support-bundle
```

Add `--batch-ids batch-a,batch-b` when validating specific A/B batches. Add `--include-database-backup` only when the operator has approved storing a full database backup in the selected output directory.

## Readiness Endpoint

`GET /api/operations/readiness` returns:

- Redacted runtime config.
- Key path writability.
- Worker and Lark connector status.
- Production checks with status, detail, and action.
- Export URLs for observability, performance, readiness, artifact retention, debug job bundles, and the operations support bundle.

No API key, token, app secret, authorization code, or user token is returned.

## Operational Exports

- Observability summary: `/api/observability/summary`
- Performance summary: `/api/performance/summary`
- Debug job export: `/api/exports/debug-jobs.zip`
- Production readiness: `/api/operations/readiness`
- Artifact retention dry run: `/api/operations/artifact-retention`
- Artifact retention cleanup: `POST /api/operations/artifact-retention/cleanup`
- SQLite database backup: `/api/operations/database-backup.zip`
- Pilot gate: `/api/operations/pilot-gate`
- Operations support bundle: `/api/operations/support-bundle.zip`
- Feishu bot setup package: `/api/lark/bot/setup-package.zip`

The operations support bundle is a ZIP intended for production-candidate incident review. It contains readiness, observability, performance, Worker status, artifact retention dry-run output, pilot gate output, Feishu bot preflight evidence, Lark operation audits, and spreadsheet writeback audits. It does not include API keys, app secrets, auth codes, user tokens, or model credential material.

`GET /api/operations/database-backup.zip` exports the configured SQLite database file and SQLite sidecar files when present. This is a data backup, not a redacted support bundle; store it only in an approved secure location. Managed non-SQLite databases should use their platform backup mechanism instead.

## Pilot Gate

`GET /api/operations/pilot-gate` gives a repeatable go/no-go check for real-scale validation. It combines:

- Production readiness level.
- Recent batch A/B comparison.
- Completed real sample coverage.
- Best batch success rate, P95 latency, and estimated cost.
- Model call errors and writeback failures.
- Lark operation failure audits.
- `model_runner` fairness lock verification.

Default thresholds are conservative for pilot entry: 20 completed samples, 80% success rate, P95 below 12 seconds, zero model call errors, zero writeback failures, and zero Lark operation failures. Operators can override thresholds through query parameters for smaller dogfood runs, but the production-candidate review should record the thresholds used.

## Lark Operations

- Use `Lark Connector` status and `/api/lark/scopes/check` before live writeback.
- Use `/api/lark/operation-audits` to inspect recent Lark command results and missing scopes.
- Use `POST /api/lark/bot/commands/preview` to validate XiaoD text command parsing before wiring the long-connection consumer to a real chat.
- For high-risk sheet writes, create and confirm a Lark write confirmation before writing if the operator workflow requires explicit confirmation.
- For user authorization, create a Lark auth session, complete authorization in Lark, then mark the session complete. The system stores state and status only; no token or authorization code is persisted.

## XiaoD Long Connection Entry Protocol

`POST /api/lark/bot/commands/preview` maps a XiaoD text command to a Debug Agent action and card response. It records a `bot` service entry in Lark operation audit but does not execute write actions directly.

XiaoD product traffic uses long connection only. Set `LARK_EVENT_MODE=long_connection`, `LARK_CLI_IDENTITY=bot`, `LARK_CLI_PROFILE=xiaoD`, and run `scripts/lark_bot_long_connection_consumer.py --transport sdk`. This mode does not require a public callback URL, `LARK_BOT_VERIFICATION_TOKEN`, `LARK_BOT_ENCRYPT_KEY`, or webhook probe evidence. The preflight and go-live gate instead check `im.message.receive_v1` schema support, SDK card action support for `card.action.trigger`, `im:message.p2p_msg:readonly`, `im:message:send_as_bot`, `sheets:spreadsheet:readonly`, `docs:document.media:download`, event subscription acknowledgement, and target chat membership acknowledgement. Card button clicks are accepted only when the SDK long-connection consumer logs the `card.action.trigger` handling path.

`POST /api/lark/bot/events` remains as a legacy HTTP parser and local diagnostic endpoint. Do not use it as the XiaoD production acceptance path. If deliberately testing webhook compatibility, it still verifies `LARK_BOT_ENCRYPT_KEY` signatures, decrypts encrypted callbacks, validates `LARK_BOT_VERIFICATION_TOKEN`, and returns URL verification challenges.

Before wiring a real Feishu app, run `GET /api/lark/bot/preflight` or click `加载机器人上线预检` in the operations page. The response includes `event_mode`. For XiaoD, callback URL, Verification Token, Encrypt Key, and webhook probe are non-required; preflight checks XiaoD bot identity/profile, `im.message.receive_v1` schema support, SDK card action support, required IM receive/send, table read, and attachment download scopes, recent permission failures, and pending/failed bot command backlog. It also returns `operator_required_items`, a setup checklist that names the owner of each real-app step: Debug Agent operator, Feishu app admin, workspace admin, or security admin. It does not send a real Feishu message.

Use `GET /api/lark/bot/permission-checklist` to get the machine-readable permission list and current blocking scopes. Use `GET /api/lark/bot/setup-package.zip` or the `下载接入交付包` link in the preflight panel when handing work to a Feishu app administrator. The package contains `preflight.json`, `permission-checklist.json`, `permission-checklist.md`, `setup-checklist.json`, `setup-checklist.md`, `feishu-admin-handoff.md`, `required-scopes.json`, and a long-connection diagnostic command file. It does not include secrets; real app secrets must stay in approved runtime configuration or secret storage.

When an external administrator finishes a manual setup item, record it through the `记录确认` form in `机器人上线预检` or `POST /api/lark/bot/setup-acknowledgements/{item_key}` with `actor`, `evidence`, and optional `note`. These acknowledgements are append-only audit records; preflight uses the latest acknowledgement only for items that cannot be verified automatically, such as event subscription, app visibility, target chat membership, and webhook probe execution. In long connection mode, event subscription, IM scope, and target chat membership acknowledgements are the manual go-live evidence; webhook probe acknowledgement is not required.

Use `GET /api/lark/bot/go-live-gate` or click `加载机器人真实上线门禁` before the first real Feishu dogfood. The gate combines production readiness, bot preflight, required setup items, manual acknowledgements, recent missing scopes, pending bot commands, and failed bot commands into one `allowed` decision. `allowed=true` is required before sending visible bot replies in a real chat.

Task 5 lifecycle dogfood must be driven from the real Feishu conversation. Send the spreadsheet request as a real `post.at` message to XiaoD in the Dogfood chat, then confirm execution by card action if available. If card clicking cannot be automated, send natural-language replies such as `继续执行` and `不同步` from the same development user so XiaoD handles the decision. Do not call pending confirm, writeback decision, or writeback APIs directly from a terminal to simulate the user. Terminal access is only for starting backend/consumer, sending the real development-role message, reading logs, and querying durable state. Record the marker, Feishu `message_id`, pending command, XiaoD run, batch, jobs, reports, writeback decision, and final `completed_summary`.

The real-app setup checklist currently covers:

- Set `LARK_EVENT_MODE=long_connection`.
- Configure `LARK_CLI_IDENTITY=bot` and `LARK_CLI_PROFILE=xiaoD`.
- Run `scripts/lark_bot_long_connection_consumer.py --transport sdk`.
- Subscribe `im.message.receive_v1` and confirm the consumer receives it.
- Enable SDK card action handling for `card.action.trigger`, or use confirm links/natural-language confirmation as fallback.
- Grant bot product permissions such as `im:message.p2p_msg:readonly`, `im:message:send_as_bot`, `sheets:spreadsheet:readonly`, and `docs:document.media:download`.
- Enable trusted actor enforcement for production-candidate write-risk commands.
- Add the bot to the target pilot chat or open the app visibility range.
- Verify with a real `/debug status` message and one real badcase draft flow.

The callback URL, Verification Token, Encrypt Key, card webhook callback, and webhook probe items are retained only for legacy diagnostics and are marked non-required for XiaoD.

Write-risk commands must use the pending command flow:

1. `POST /api/lark/bot/commands/pending` creates a pending command from the same text command payload.
2. `GET /api/lark/bot/commands/pending?status=pending` lists pending commands for the Web operations console.
3. `POST /api/lark/bot/commands/pending/{command_id}/confirm` confirms and executes it.
4. Confirmed single-case commands submit `/api/cases/{case_id}/debug-jobs`.
5. Confirmed batch commands submit `/api/debug-jobs/batch`.
6. `GET /api/lark/bot/commands/pending/{command_id}/reply-preview` renders the Feishu reply markdown and CLI delivery arguments.
7. `POST /api/lark/bot/commands/pending/{command_id}/send-reply` sends the reply through `LarkConnector`; it defaults to `dry_run=true` and requires an explicit `dry_run=false` request before any visible IM message is sent.

Pending commands expire and cannot be executed after expiry. Read-only commands cannot be converted to pending commands.

The Web operations page exposes `加载机器人命令` to list, filter, confirm, and preview bot replies without using raw API calls.

Bot replies prefer `message_id` and use `im +messages-reply` when the original Feishu message is available. If no `message_id` is present, replies fall back to `chat_id` or `open_id` with `im +messages-send`. The connector records both the low-level IM operation and the higher-level bot reply audit entry. Reply markdown intentionally summarizes command id, original command, status, submitted job or batch id, and the follow-up `/debug job` or `/debug batch` query.

Supported command examples:

- `/debug help`
- `/debug status`
- `/debug pilot-gate`
- `/debug job <job_id>`
- `/debug batch <batch_id>`
- `/debug run case <case_id>`
- `/debug batch run case-a,case-b`

Commands that create jobs are marked as write-risk actions and require operator confirmation before any future event handler should execute them.

## Recovery

- If jobs are stuck in `running`, the worker recovery path will recover stale jobs after `DEBUG_AGENT_STALE_RUNNING_JOB_SECONDS`.
- If writeback fails, inspect writeback audit and Lark operation audit before retrying.
- If model usage exceeds budget, pause submissions or raise the configured budget.
- If artifact paths are not writable, fix deployment permissions before restarting the worker.
- If artifact usage grows unexpectedly, inspect `/api/operations/artifact-retention`; cleanup defaults to dry run and real deletion requires `dry_run=false` plus `confirmation=DELETE_EXPIRED_ARTIFACTS`.
- If pilot gate fails, resolve failed checks first; do not treat a single successful small batch as production evidence.

# Debug Agent 企业级多模态调试系统

Debug Agent 是一个面向部门落地的多模态 badcase 调试系统。它通过飞书/Lark 机器人“小D”承接真实用户入口，把用户提交的样本、表格、文档、图片、视频和附件转成可审计的 `DebugJob`，再通过假设驱动的调试流程沉淀证据、生成报告，并把经过确认的调试经验写入向量知识库。

这个项目不是脚本 demo，也不是只会调用接口的聊天壳。它包含后端 API、前端控制台、Docker 部署、异步 worker、小D飞书长连接、运维预检、报告导出、RAG 知识库和 DebugLesson 自优化闭环。

## 项目定位

Debug Agent 服务于评测、算法、业务质量、平台运维和项目协作同学，解决多模态模型 badcase 调试过程不可复现、证据不透明、报告不可读、经验无法沉淀的问题。

核心原则：

- 证据优先：没有证据支撑，不能声称找到根因。
- 透明闭环：证据耗尽是合法结论，必须说明停止原因和缺失证据。
- 操作可控：创建任务、批量调试、表格写回、Base 写回等写风险操作必须经过确认。
- 真实入口：小D/飞书交互是产品入口，终端脚本不能假装用户路径。
- 持续学习：静态项目知识和动态 DebugLesson 都要进入 RAG，用于后续问答和调试规划增强。

## 系统能力

- 支持 JSONL、CSV、飞书表格、Base、飞书文档、附件、图片、视频等多种 badcase 输入。
- 支持单样本 `DebugJob` 和批量 `DebugBatch`。
- 支持 worker 队列、暂停、恢复、取消、重试、并发控制和 stale running job 恢复。
- 支持 case intake、experiment planner、model runner、judge comparator、evidence artifact、root cause report、writeback operator 等 Agent 角色。
- 支持 run stages、evidence ledger、artifact 文件、recommended actions、human handoff 和最终报告。
- 支持 bounded hypothesis loop、controlled probe、causal comparison、verified root cause 和 evidence exhausted stop。
- 支持飞书表格同步、表格重跑、报告字段写回、Base 写回、写回确认和审计。
- 支持小D onboarding 卡片、确认卡片、进度卡片、报告链接和用户视图。
- 支持 SQLite 持久化向量库、`local-hash-v1` 本地 embedding、混合检索和 citations。
- 支持 readiness、pilot gate、performance summary、support bundle、database backup、artifact retention 和 bot setup package。

## 总体架构

运行服务：

- `backend`：FastAPI 后端 API 服务。
- `worker`：异步 DebugJob worker。
- `frontend`：React/Vite 前端，由 nginx 托管并反向代理后端接口。
- `lark-bot-consumer`：可选的小D飞书长连接 consumer，用于真实飞书消息和卡片点击。

核心后端模块：

- `debug_agent.api`：HTTP 路由、小D路由、运维路由和运行时组装。
- `debug_agent.jobs`：任务服务、worker、表格重跑和自动闭环。
- `debug_agent.debug_closure`：假设循环、probe 规划、因果比较和闭环策略。
- `debug_agent.reports`：报告生成、run view、citation、recommended actions 和飞书文档渲染。
- `debug_agent.assistant`：项目助手、RAG、向量库和 DebugLesson 入库。
- `debug_agent.lark`：飞书连接器、命令解析、回复 payload、进度卡片和小D编排。
- `debug_agent.storage`：SQLite schema、repository、审计记录、pending command 和行映射。
- `debug_agent.spreadsheets`：飞书表格读取、同步、重跑、写回和审计策略。

## 用户入口

- 前端控制台：`http://localhost:8080`
- 后端健康检查：`http://localhost:8000/health`
- 小D使用手册：`http://localhost:8080/xiaod/views/manual`
- 知识库状态：`http://localhost:8080/api/assistant/knowledge/status`
- 运维 readiness：`http://localhost:8000/api/operations/readiness`

小D应该引导用户完成：

- 提交 badcase 或表格链接。
- 补齐字段并确认是否创建任务。
- 查询 job 或 batch 进度。
- 阅读报告、证据边界和停止原因。
- 决定是否同步或写回。
- 查询项目知识、使用方式和运维状态。

## 知识库和 RAG

初始项目知识位于：

```text
backend/src/debug_agent/assistant/knowledge/
```

当前包含 10 份长文档，每份不少于 500 行：

- `product_overview.md`
- `enterprise_delivery_handbook.md`
- `user_quickstart_manual.md`
- `xiaod_interaction_rules.md`
- `debug_workflow_and_state_machine.md`
- `multimodal_debug_playbook.md`
- `report_and_evidence_guide.md`
- `card_ux_and_onboarding.md`
- `operations_runbook.md`
- `rag_vector_knowledge_and_learning.md`

RAG 实现方式：

- Markdown 文档会切分为 `KnowledgeChunk`。
- 文档、chunk 和 DebugLesson 会持久化到 SQLite。
- 默认 embedding provider 是确定性的 `local-hash-v1`，便于离线测试和可重复验证。
- 检索策略融合向量相似度、关键词重合、标题/来源权重和 manual source bonus。
- Debug 历史可以蒸馏为 `DebugLesson` 并作为动态知识进入检索。
- RAG 可以增强问答、解释和规划，但不能替代当前任务证据。

知识库状态检查：

```powershell
curl.exe http://localhost:8080/api/assistant/knowledge/status
```

知识检索检查：

```powershell
$body = @{ query = "企业级落地交付标准"; limit = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8080/api/assistant/knowledge/search `
  -ContentType "application/json" `
  -Body $body
```

## Docker 部署

Docker 是当前本地 production-candidate 部署路径。它构建稳定镜像，而不是每次容器启动时临时安装 Python 和 Node 依赖。

启动基础服务：

```powershell
docker compose up -d --build backend worker frontend
docker compose ps
curl.exe http://localhost:8080/health
curl.exe http://localhost:8080/api/assistant/knowledge/status
```

默认端口：

- `8080`：nginx 前端入口和反向代理。
- `8000`：后端直连入口，用于运维检查。

持久化 volume：

- `backend_artifacts`：SQLite 数据库、向量索引、DebugLesson、运行产物、报告和导出包。
- `lark_cli_data`：可选的小D consumer 使用的 `lark-cli` profile 数据。
- `lark_consumer_state`：可选的小D consumer 事件去重状态。

小D飞书长连接只在飞书/Lark app 凭据和权限确认后启动：

```powershell
docker compose --profile lark up -d --build lark-bot-consumer
docker compose logs -f lark-bot-consumer
```

正常重启不要执行 `docker compose down -v`。这个命令会删除 `backend_artifacts`，同时删除 SQLite 数据库、RAG 向量索引、DebugLesson 历史和生成报告。

## 本地开发

常用命令：

- `make test`：运行后端和前端测试。
- `make lint`：运行后端 Ruff 和前端 lint。
- `make typecheck`：运行 Python mypy 和 TypeScript typecheck。
- `make dev`：启动 compose stack。
- 在 `backend` 目录运行 `python -m ruff check .`：后端静态检查。
- 在 `backend` 目录运行 `python -m pytest`：后端测试。
- 在 `frontend` 目录运行 `npx --yes pnpm@9.15.4 test -- --run`：前端测试。

PowerShell production-candidate 后端启动：

```powershell
powershell -File scripts/start-production.ps1
```

预检和试点证据收集：

```powershell
python scripts/production_preflight.py --base-url http://127.0.0.1:8000
```

```powershell
python scripts/pilot_validation_record.py `
  --base-url http://127.0.0.1:8000 `
  --output-dir dogfood-output/pilot-validation
```

## 配置说明

本地开发和 Docker 部署都从 `.env.example` 复制出 `.env`。真实密钥只能放在本地 `.env`、shell 环境变量或正式 secret storage，不能提交到代码库。

关键运行变量：

- `DEBUG_AGENT_DATABASE_URL`
- `DEBUG_AGENT_IMAGE_ARTIFACT_DIR`
- `DEBUG_AGENT_REPORT_BASE_URL`
- `DEBUG_AGENT_DOCKER_REPORT_BASE_URL`
- `DEBUG_AGENT_FRONTEND_PORT`
- `DEBUG_AGENT_MODEL_PROVIDER`
- `DEBUG_AGENT_AUTO_WRITEBACK_ENABLED`
- `DEBUG_AGENT_AUTO_CLOSURE_ENABLED`
- `DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR`
- `DEBUG_AGENT_USAGE_BUDGET_UNITS`
- `DEBUG_AGENT_ENFORCE_USAGE_BUDGET`
- `LARK_EVENT_MODE`
- `LARK_CLI_PROFILE`
- `LARK_CLI_IDENTITY`
- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `ARK_API_KEY`
- `ARK_CHAT_MODEL_ID`
- `ARK_VIDEO_MODEL_ID`

模型路由区分小D/assistant 对话、强推理 meta agent、轻量 agent 和锁定状态的 source replay `model_runner`。live model 测试默认不打开，需要显式配置后再执行。

## 飞书/Lark 和小D

小D产品路径使用飞书长连接。HTTP webhook parser 只作为本地诊断和兼容路径，不作为产品验收入口。

推荐小D配置：

```env
LARK_EVENT_MODE=long_connection
LARK_CLI_IDENTITY=bot
LARK_CLI_PROFILE=xiaoD
DEBUG_AGENT_AUTO_WRITEBACK_ENABLED=0
```

真实 dogfood 前必须完成：

- 检查 `GET /api/lark/bot/preflight`。
- 检查 `GET /api/lark/bot/permission-checklist`。
- 导出 `GET /api/lark/bot/setup-package.zip` 给飞书 app 管理员。
- 对事件订阅、bot 可见范围、目标群成员等人工项写入 acknowledgement。
- 检查 `GET /api/lark/bot/go-live-gate`。
- 从真实飞书群聊驱动生命周期验证，不要直接在终端调用 confirm/writeback API 假装用户操作。

写风险操作必须进入 pending command 或 writeback confirmation 流程。系统不能在没有持久状态和证据的情况下声称已经创建任务、更新表格或找到根因。

## 报告和证据链

最终报告必须展示：

- 原始 case 和观察到的失败现象。
- run stages 和 evidence ledger。
- supported root-cause candidates。
- controlled probe 结果。
- causal comparison 结果。
- recommended actions 和 human handoff。
- writeback decision 和 audit 状态。
- 明确的证据边界、停止原因和缺失证据。

如果没有 supported root cause，正确结论是 `stopped_evidence_exhausted`，并说明已审阅证据、探索预算、缺失证据和下一步建议。

## 运维入口

主要运维接口：

- `/health`
- `/api/operations/readiness`
- `/api/operations/pilot-gate`
- `/api/operations/artifact-retention`
- `/api/operations/support-bundle.zip`
- `/api/operations/database-backup.zip`
- `/api/observability/summary`
- `/api/performance/summary`
- `/api/lark/operation-audits`
- `/api/lark/bot/go-live-gate`

production-candidate 运维说明见：

```text
docs/operations/production-runbook.md
```

## 重要文档

- `docs/operations/production-runbook.md`：部署和运维手册。
- `docs/operations/pilot-validation-template.md`：试点验证记录模板。
- `docs/operations/xiaod-bot-product-protocol.md`：小D产品协议。
- `docs/operations/xiaod-bot-permission-checklist.md`：bot 权限清单。
- `docs/operations/xiaod-implementation-log.md`：小D实现历史。
- `docs/operations/hypothesis-debug-closure-implementation-log.md`：假设闭环实现记录。
- `backend/src/debug_agent/assistant/knowledge/`：RAG 源文档。

## 验收清单

交付前至少确认：

- Docker 基础服务 `backend`、`worker`、`frontend` 启动正常。
- `http://localhost:8080/health` 能通过 nginx 返回后端 OK。
- `/api/assistant/knowledge/status` 返回 10 份文档和非零 chunk。
- 知识检索能返回相关手册 chunk 和 citation。
- 小D手册页能通过 `/xiaod/views/manual` 打开。
- 项目相关问题能走 RAG 引用回答。
- 非项目通用问题不会错误附带项目 citation。
- worker 状态可见，job 生命周期 API 可用。
- 报告透明展示证据、停止原因和缺失证据。
- 写回默认关闭或必须经过显式确认。
- 真实飞书 dogfood 前完成 preflight 和 go-live gate。
- 必要测试和静态检查通过。

## 验证命令

最近使用过的重点验证命令：

```powershell
cd backend
python -m ruff check .
python -m pytest tests/api/test_assistant_chat.py `
  tests/assistant/test_knowledge_base.py `
  tests/assistant/test_debug_lessons.py `
  tests/api/lark_bot/test_xiaod_turn_context.py `
  tests/api/test_xiaod_user_views.py
python -m pytest tests/test_env_example.py tests/test_settings.py
```

Docker 验证：

```powershell
docker compose config
docker compose up -d --build backend worker frontend
docker compose --profile lark build lark-bot-consumer
docker compose ps
```

## 质量标准

功能完成必须同时满足实现、测试、文档和本地验证。调试类功能不能伪造根因，不能把没有证据支持的推断写成结论。证据耗尽并说明边界，是可验收、可复盘的合法结果。

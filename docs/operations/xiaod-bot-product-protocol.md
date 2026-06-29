# 小D Bot 产品协议

本文档定义小D作为 Debug Agent 企业入口时的产品协议、控制权边界和验收口径。文档只描述正式产品行为，不记录临时 dogfood ID、真实表格 token、附件 token、app secret、授权码或临时公网调试地址。

## 目标

小D是 Debug Agent 在飞书里的用户入口，不是后端 API 的命令行外壳，也不拥有独立业务状态。用户可以用自然语言、飞书链接和附件提交 badcase；小D负责识别意图、调用后端草稿和任务能力、转述缺口、发送确认卡片、回传进度和报告链接。

## 完成定义

- 用户无需知道内部样本 ID、接口路径或 pending command。
- 私聊支持自然语言；群聊只响应 `@小D`、回复小D消息或显式 `/debug`。
- 信息不全时只保存草稿并追问缺口，不创建任务。
- 信息齐全后进入待确认状态；确认前不启动 `DebugJob`。
- 确认后创建 `DebugCase` 和 `DebugJob`。
- 任务状态、完成摘要、报告链接和写回确认入口能回到飞书。
- 飞书链接、图片、视频和文件附件进入统一输入协议。
- 权限不足时给出可执行的管理员处理说明。
- 写操作必须有确认门禁，不能静默写飞书表格或 Base。
- 后端、consumer、前端操作台和 Docker 运行方式保持一致。

## 控制权边界

- 规则和状态机决定是否创建任务、是否写回、是否需要确认。
- LLM 可以辅助理解用户意图和组织回复，但不能绕过后端状态机。
- 小D不能在没有持久状态的情况下声称任务已创建。
- 小D不能在没有证据的情况下声称根因已确认。
- 小D不能在没有确认和审计的情况下声称表格或 Base 已写回。

## 主要用户流程

### 1. 首次使用

- 用户发送“帮助”“怎么用”或第一次进入会话时，小D发送 onboarding 卡片。
- 卡片展示摘要能力，并链接到 `/xiaod/views/manual`。
- 卡片按钮只能打开用户视图或手册，不直接暴露 JSON。

### 2. 提交 badcase

- 用户发送自然语言、飞书链接或附件。
- 小D解析输入来源，调用后端创建或更新 badcase draft。
- 后端判断字段是否齐全。
- 字段缺失时，小D追问具体缺口。
- 字段齐全时，小D发送确认卡片。

### 3. 确认执行

- 用户点击确认按钮或用明确自然语言确认。
- 后端创建 `DebugCase` 和 `DebugJob`。
- 任务进入 worker 队列。
- 小D发送任务入口、进度入口和取消/查看方式。

### 4. 查看结果

- 任务完成后，小D回传最终报告入口。
- 报告必须展示证据链、候选根因、验证情况、停止原因和缺失证据。
- 如果证据耗尽，报告应明确 `stopped_evidence_exhausted`，不能包装成已找到根因。

### 5. 写回确认

- 表格或 Base 来源任务完成后，小D提供写回确认入口。
- 用户确认前不执行写回。
- 写回结果进入 audit。
- 失败时区分可重试错误和终态错误。

## 长连接协议

- 产品主链路使用 `LARK_EVENT_MODE=long_connection`。
- consumer 使用 SDK transport，同时处理 `im.message.receive_v1` 和 `card.action.trigger`。
- HTTP webhook parser 只保留为兼容诊断路径。
- 真实上线前必须通过 preflight 和 go-live gate。

## 需要后端保证的状态

- badcase draft 状态。
- pending command 状态。
- `DebugJob` 和 `DebugBatch` 状态。
- worker 状态。
- completion notification outbox 状态。
- writeback confirmation 和 audit 状态。
- setup acknowledgement 状态。
- operation audit 状态。

## 验收口径

- 小D能在真实飞书会话中完成从输入到草稿的转换。
- 信息不全时不创建任务。
- 信息齐全后必须经过确认。
- 确认后任务能在后端和前端查询到。
- 报告入口可打开，且展示证据边界。
- 表格/Base 写回必须经过确认。
- RAG 问答能引用项目知识库。
- 普通非项目问题不会错误附带项目 citation。
- 长连接 consumer、backend、worker、frontend 能通过 Docker 部署启动。

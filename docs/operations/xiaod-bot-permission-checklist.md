# 小D Bot 飞书权限申请清单

本文档用于飞书 app 管理员、工作区管理员和 Debug Agent 运维人员对齐小D上线所需权限。文档只记录权限口径和验收方法，不记录真实 app secret、授权码、用户 token、内部表格 token、附件 token 或临时公网调试地址。

## 权限原则

- 小D产品路径使用长连接，`LARK_EVENT_MODE=long_connection` 是默认上线形态。
- HTTP webhook 只作为兼容诊断入口，不作为小D真实验收主链路。
- 读权限、写权限和附件下载权限分开申请，避免用过大的权限掩盖缺口。
- 表格单元格附件属于文档 media 场景，下载权限按 `docs:document.media:download` 处理。
- 表格写回、Base 写回和任务创建必须经过确认门禁和审计记录。
- 权限检查结果应通过 API、上线门禁和真实飞书消息验证，而不是人工口头确认。

## 机器可读接口

```text
GET /api/lark/bot/permission-checklist
GET /api/lark/bot/preflight
GET /api/lark/bot/go-live-gate
GET /api/lark/bot/setup-package.zip
```

运维支持包和机器人接入交付包会导出权限清单、setup checklist 和管理员交接说明。导出包不应包含密钥、授权码或用户 token。

## 必需权限和配置

| 类别 | 权限 / 配置 | 用途 | 验收方式 |
| --- | --- | --- | --- |
| 事件订阅 | `im.message.receive_v1` | 长连接接收私聊、群聊 @ 小D消息 | 小D能收到真实消息并生成后端 turn handle 记录 |
| 卡片交互 | `card.action.trigger` SDK 支持 | 支持确认提交、取消草稿、写回确认等按钮 | 长连接 consumer 记录 card action handling |
| IM 读 | `im:message.p2p_msg:readonly` 或管理员配置的等价 IM 读取权限 | 读取用户消息、mentions 和附件元信息 | preflight 不再报告 IM 读取缺口 |
| IM 写 | `im:message:send_as_bot` | 小D回复消息、发送卡片和报告链接 | 真实会话中可发送状态回复 |
| 表格读 | `sheets:spreadsheet:readonly` | 读取表格行、字段、富文本和附件 token | 表格链接可生成 badcase 草稿 |
| 文档媒体下载 | `docs:document.media:download` | 下载表格单元格附件和文档 media 输入 | 附件下载不再停在 missing scope |
| 文档写 | `docx:document` | 生成飞书 Docx 报告并返回云文档链接 | 报告生成开启后可创建文档 |

## 建议权限

| 类别 | 权限 / 配置 | 用途 |
| --- | --- | --- |
| 表格写 | `sheets:spreadsheet` | 把状态、根因、报告链接、推荐动作写回表格 |
| 文档读 | `docx:document:readonly` | 读取用户发来的飞书文档正文并提取 badcase |
| 云盘元数据读 | `drive:drive.metadata:readonly` 或等价权限 | 识别普通文件名、类型和权限状态 |
| 云盘普通文件下载 | `drive:file:download` | 下载用户直接发送的云盘普通文件 |
| Base 读 | `bitable:app:readonly` 或等价权限 | 读取 Base 表、记录和字段 |
| Base 写 | `bitable:app` | 写回 Base 台账记录 |

## 上线确认项

- 已配置 `LARK_EVENT_MODE=long_connection`。
- 已配置 `LARK_CLI_IDENTITY=bot` 和 `LARK_CLI_PROFILE=xiaoD`。
- 飞书 app 已订阅消息事件，并确认长连接 consumer 能收到事件。
- bot 已加入目标试点群，或 app 可见范围已覆盖目标用户。
- `GET /api/lark/bot/preflight` 不存在阻塞项。
- `GET /api/lark/bot/go-live-gate` 返回允许上线。
- 首次真实 dogfood 由飞书会话触发，不直接调用后端确认接口模拟用户。

## 缺权限时的产品行为

- 读权限缺失时，小D应说明缺失权限和需要管理员处理的事项。
- 下载权限缺失时，草稿可以保留，但不能伪造媒体输入。
- 写权限缺失时，报告仍可生成；写回动作应停在确认或失败审计状态。
- 任何权限缺口都应进入 operation audit 或 preflight 结果，便于追踪。

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from html import escape
from typing import Literal
from urllib.parse import urlencode

from debug_agent.api.badcase_intake_parsers import _clip_text
from debug_agent.lark.bot import LarkBotReplyPayload
from debug_agent.storage.repository import LarkBotBadcaseDraft


LarkBotBadcaseAction = Literal[
    "confirm_badcase_draft",
    "cancel_badcase_draft",
    "writeback_spreadsheet",
    "writeback_base",
]


class LarkBadcaseRenderer:
    def __init__(
        self,
        *,
        report_base_url: Callable[[], str],
        token_secret: Callable[[LarkBotBadcaseDraft], str],
        reply_target_type: Callable[[LarkBotBadcaseDraft], Literal["reply", "chat"]],
        idempotency_key: Callable[[str], str],
        reply_cli_args: Callable[[LarkBotReplyPayload, str, bool], list[str]],
        spreadsheet_writeback_target: Callable[[str], tuple[str, str, str] | None],
        base_writeback_target: Callable[[str], tuple[str, str, str] | None],
    ) -> None:
        self._report_base_url = report_base_url
        self._token_secret = token_secret
        self._reply_target_type = reply_target_type
        self._idempotency_key = idempotency_key
        self._reply_cli_args = reply_cli_args
        self._spreadsheet_writeback_target = spreadsheet_writeback_target
        self._base_writeback_target = base_writeback_target

    def confirmation_card_payload(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        dry_run: bool,
    ) -> LarkBotReplyPayload:
        payload = LarkBotReplyPayload(
            command_id=f"badcase-{draft.draft_id}-confirm",
            action_kind="badcase_confirmation",
            status=draft.status,
            target_type=self._reply_target_type(draft),
            message_id=draft.message_id,
            chat_id=draft.chat_id,
            user_id=draft.open_id,
            markdown=self.confirmation_markdown(draft=draft),
            message_type="interactive",
            content=self.confirmation_card(draft=draft),
            idempotency_key=self._idempotency_key("card"),
        )
        return payload.model_copy(
            update={
                "delivery_args": self._reply_cli_args(payload, "bot", dry_run),
            }
        )

    def confirmation_markdown(self, *, draft: LarkBotBadcaseDraft) -> str:
        return "\n".join(
            [
                "## Debug Agent 等待确认",
                "",
                f"- 草稿编号：`{draft.draft_id}`",
                f"- 原始输入：{draft.input_source}",
                f"- 错误现象：{draft.issue_summary or '未填写'}",
                "",
                "请点击卡片按钮确认提交，或直接回复“确认提交”。确认前不会创建任务。",
            ]
        )

    def confirmation_card(self, *, draft: LarkBotBadcaseDraft) -> dict[str, object]:
        console_url = self._report_base_url().rstrip("/")
        fallback_confirm_url = self.action_url(
            draft=draft,
            action="confirm_badcase_draft",
        )
        fallback_cancel_url = self.action_url(
            draft=draft,
            action="cancel_badcase_draft",
        )
        confirm_value = {
            "action": "confirm_badcase_draft",
            "draft_id": draft.draft_id,
            "create_job": True,
        }
        cancel_value = {
            "action": "cancel_badcase_draft",
            "draft_id": draft.draft_id,
        }
        actions: list[dict[str, object]] = [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "确认提交"},
                "type": "primary",
                "value": confirm_value,
                "behaviors": [{"type": "callback", "value": confirm_value}],
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "取消草稿"},
                "type": "danger",
                "value": cancel_value,
                "behaviors": [{"type": "callback", "value": cancel_value}],
            },
        ]
        if fallback_confirm_url:
            actions.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "打开确认页"},
                    "type": "default",
                    "url": fallback_confirm_url,
                }
            )
        if fallback_cancel_url:
            actions.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "打开取消页"},
                    "type": "default",
                    "url": fallback_cancel_url,
                }
            )
        actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "打开操作台"},
                "type": "default",
                "url": console_url,
            }
        )
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "orange",
                "title": {"tag": "plain_text", "content": "确认提交 Debug 任务"},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": "\n".join(
                        [
                            f"**草稿编号**：`{draft.draft_id}`",
                            f"**原始输入**：{_clip_text(draft.input_source, 180)}",
                            f"**错误现象**：{_clip_text(draft.issue_summary or '未填写', 240)}",
                            "",
                            "点击确认后会创建 DebugCase 和 DebugJob；确认前不会执行。",
                            "如果飞书卡片回调不可用，可以打开确认页或直接回复“确认提交”。",
                        ]
                    ),
                },
                {
                    "tag": "action",
                    "actions": actions,
                },
            ],
        }

    def action_url(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        action: LarkBotBadcaseAction,
    ) -> str:
        token = self.action_token(draft=draft, action=action)
        if not token:
            return ""
        if action == "writeback_spreadsheet":
            path = "writeback-link"
            query = urlencode({"token": token})
        elif action == "writeback_base":
            path = "base-writeback-link"
            query = urlencode({"token": token})
        else:
            path = "confirm-link"
            query = urlencode({"action": action, "token": token})
        return (
            f"{self._report_base_url().rstrip('/')}/api/lark/bot/badcase-drafts/"
            f"{draft.draft_id}/{path}?{query}"
        )

    def action_token(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        action: LarkBotBadcaseAction,
    ) -> str:
        secret = self._token_secret(draft)
        if not secret:
            return ""
        message = json.dumps(
            {
                "action": action,
                "chat_id": draft.chat_id,
                "draft_id": draft.draft_id,
                "message_id": draft.message_id,
                "open_id": draft.open_id,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hmac.new(
            secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def action_page_html(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        action: Literal["confirm_badcase_draft", "cancel_badcase_draft"],
        token: str,
    ) -> str:
        is_confirm = action == "confirm_badcase_draft"
        title = "确认提交 Debug 任务" if is_confirm else "取消 badcase 草稿"
        button_label = "确认提交" if is_confirm else "确认取消"
        action_path = (
            f"/api/lark/bot/badcase-drafts/{draft.draft_id}/confirm-link?"
            f"{urlencode({'action': action, 'token': token})}"
        )
        fields = [
            ("草稿编号", draft.draft_id),
            ("原始输入", _clip_text(draft.input_source, 240)),
            ("错误现象", _clip_text(draft.issue_summary or "未填写", 240)),
        ]
        detail_items = "\n".join(
            f"<li><strong>{escape(label)}</strong>：{escape(value)}</li>"
            for label, value in fields
        )
        return _action_page(
            title=title,
            hint="这是小D从飞书卡片打开的二次确认页。提交前不会创建或取消任务。",
            detail_items=detail_items,
            action_path=action_path,
            button_label=button_label,
        )

    def spreadsheet_writeback_page_html(
        self, *, draft: LarkBotBadcaseDraft, token: str
    ) -> str:
        target = (
            self._spreadsheet_writeback_target(draft.submitted_job_id)
            if draft.submitted_job_id
            else None
        )
        target_text = "/".join(target) if target is not None else "未找到来源表格行映射"
        action_path = (
            f"/api/lark/bot/badcase-drafts/{draft.draft_id}/writeback-link?"
            f"{urlencode({'token': token})}"
        )
        fields = [
            ("草稿编号", draft.draft_id),
            ("任务编号", draft.submitted_job_id or "未提交"),
            ("目标表格行", target_text),
            ("写回内容", "状态、根因摘要、推荐动作和报告链接"),
        ]
        detail_items = _detail_items(fields)
        return _action_page(
            title="确认写回原表格",
            hint="这是写操作。点击确认后，小D会把调试结论写回来源表格行。",
            detail_items=detail_items,
            action_path=action_path,
            button_label="确认写回",
        )

    def base_writeback_page_html(self, *, draft: LarkBotBadcaseDraft, token: str) -> str:
        target = (
            self._base_writeback_target(draft.submitted_job_id)
            if draft.submitted_job_id
            else None
        )
        target_text = "/".join(target) if target is not None else "未找到来源 Base 记录映射"
        action_path = (
            f"/api/lark/bot/badcase-drafts/{draft.draft_id}/base-writeback-link?"
            f"{urlencode({'token': token})}"
        )
        fields = [
            ("草稿编号", draft.draft_id),
            ("任务编号", draft.submitted_job_id or "未提交"),
            ("目标 Base 记录", target_text),
            ("写回内容", "状态、根因摘要、推荐动作和报告链接"),
        ]
        detail_items = _detail_items(fields)
        return _action_page(
            title="确认写回 Base 记录",
            hint="这是写操作。点击确认后，小D会把调试结论写回来源 Base 记录。",
            detail_items=detail_items,
            action_path=action_path,
            button_label="确认写回",
        )


def action_result_html(*, title: str, lines: list[str]) -> str:
    detail_items = "\n".join(f"<li>{escape(line)}</li>" for line in lines)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2329; }}
    main {{ max-width: 720px; margin: 0 auto; border: 1px solid #dee0e3; border-radius: 12px; padding: 24px; }}
    .hint {{ color: #646a73; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <ul>{detail_items}</ul>
    <p class="hint">这个页面可以关闭。</p>
  </main>
</body>
</html>"""


def _detail_items(fields: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"<li><strong>{escape(label)}</strong>：{escape(value)}</li>" for label, value in fields
    )


def _action_page(
    *,
    title: str,
    hint: str,
    detail_items: str,
    action_path: str,
    button_label: str,
) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2329; }}
    main {{ max-width: 720px; margin: 0 auto; }}
    .card {{ border: 1px solid #dee0e3; border-radius: 12px; padding: 24px; }}
    button {{ background: #245bdb; border: 0; border-radius: 8px; color: #fff; cursor: pointer; font-size: 16px; padding: 10px 18px; }}
    .hint {{ color: #646a73; }}
  </style>
</head>
<body>
  <main class="card">
    <h1>{escape(title)}</h1>
    <p class="hint">{escape(hint)}</p>
    <ul>{detail_items}</ul>
    <form method="post" action="{escape(action_path, quote=True)}">
      <button type="submit">{escape(button_label)}</button>
    </form>
  </main>
</body>
</html>"""

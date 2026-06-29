from __future__ import annotations

from collections.abc import Mapping


def build_lark_progress_card(
    *,
    title: str,
    template: str,
    job_id: str,
    job_url: str,
    run_stages_url: str,
    report_url: str = "",
    progress: Mapping[str, object],
) -> dict[str, object]:
    percent = _progress_percent(progress)
    actions = [
        _lark_url_button("打开任务", job_url, style="primary"),
        _lark_url_button("查看运行阶段", run_stages_url),
    ]
    if report_url:
        actions.append(_lark_url_button("打开报告", report_url))
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template or "blue",
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "\n".join(
                    [
                        progress_bar(percent),
                        "",
                        f"**任务编号**：`{job_id}`",
                        f"**当前阶段**：`{_progress_text(progress, 'stage')}`",
                        f"**阶段耗时**：{_progress_text(progress, 'stage_elapsed')}",
                        f"**已完成 Agent**：{_progress_text(progress, 'completed_agents')}",
                        f"**预计下一步**：{_progress_text(progress, 'next_step')}",
                        f"**状态**：{_progress_text(progress, 'summary')}",
                        f"**说明**：{_progress_text(progress, 'detail')}",
                    ]
                ),
            },
            {
                "tag": "action",
                "actions": actions,
            },
        ],
    }


def progress_bar(percent: int) -> str:
    normalized = max(0, min(100, percent))
    filled = normalized // 10
    return f"**进度**：{'█' * filled}{'░' * (10 - filled)} {normalized}%"


def _progress_percent(progress: Mapping[str, object]) -> int:
    value = progress.get("percent", 0)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _progress_text(progress: Mapping[str, object], key: str) -> str:
    value = progress.get(key, "")
    return str(value)


def _lark_url_button(label: str, url: str, *, style: str = "default") -> dict[str, object]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "url": url,
    }

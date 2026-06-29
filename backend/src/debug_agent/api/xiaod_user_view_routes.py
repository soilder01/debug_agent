from __future__ import annotations

import json
from collections.abc import Callable
from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from debug_agent.api.schemas import DebugBatchProgressResponse, DebugJobStatus
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.reports.generator import DebugReport
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository
from debug_agent.storage.schemas import DebugRunStage


def build_xiaod_user_view_router(
    *,
    job_repository: DebugJobRepository,
    build_job_status: Callable[[DebugJobRow], DebugJobStatus],
    build_batch_progress: Callable[[str], DebugBatchProgressResponse],
    build_report: Callable[[str], DebugReport | None],
    report_base_url: Callable[[], str],
) -> APIRouter:
    router = APIRouter()
    controller = XiaoDUserViewController(
        job_repository=job_repository,
        build_job_status=build_job_status,
        build_batch_progress=build_batch_progress,
        build_report=build_report,
        report_base_url=report_base_url,
    )

    @router.get("/xiaod/views/jobs/{job_id}", response_class=HTMLResponse)
    def job_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.job_view(job_id))

    @router.get("/xiaod/views/jobs/{job_id}/report", response_class=HTMLResponse)
    def report_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.report_view(job_id))

    @router.get("/xiaod/views/jobs/{job_id}/run-stages", response_class=HTMLResponse)
    def run_stages_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.run_stages_view(job_id))

    @router.get("/xiaod/views/jobs/{job_id}/evidence-ledger", response_class=HTMLResponse)
    def evidence_ledger_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.evidence_ledger_view(job_id))

    @router.get("/xiaod/views/jobs/{job_id}/recommended-actions", response_class=HTMLResponse)
    def recommended_actions_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.recommended_actions_view(job_id))

    @router.get("/xiaod/views/jobs/{job_id}/human-handoffs", response_class=HTMLResponse)
    def human_handoffs_view(job_id: str) -> HTMLResponse:
        return HTMLResponse(controller.human_handoffs_view(job_id))

    @router.get("/xiaod/views/debug-batches/{batch_id}", response_class=HTMLResponse)
    def batch_view(batch_id: str) -> HTMLResponse:
        return HTMLResponse(controller.batch_view(batch_id))

    @router.get("/xiaod/views/manual", response_class=HTMLResponse)
    def manual_view() -> HTMLResponse:
        return HTMLResponse(controller.manual_view())

    return router


class XiaoDUserViewController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        build_job_status: Callable[[DebugJobRow], DebugJobStatus],
        build_batch_progress: Callable[[str], DebugBatchProgressResponse],
        build_report: Callable[[str], DebugReport | None],
        report_base_url: Callable[[], str],
    ) -> None:
        self._job_repository = job_repository
        self._build_job_status = build_job_status
        self._build_batch_progress = build_batch_progress
        self._build_report = build_report
        self._report_base_url = report_base_url

    def job_view(self, job_id: str) -> str:
        job = self._require_job(job_id)
        report = self._build_report(job_id)
        evidence = self._job_repository.list_evidence(job_id)
        stages = self._job_repository.list_debug_run_stages(job_id)
        document = self._job_repository.get_lark_report_document(job_id)
        report_url = (
            document.document_url
            if document is not None and document.status == "published" and document.document_url
            else self._view_url(f"/xiaod/views/jobs/{job_id}/report")
        )
        primary = [
            _metric_card("任务状态", _status_pill(job.status), "当前 DebugJob 的执行状态。"),
            _metric_card(
                "证据记录",
                f"{len(evidence)} 条",
                "Evidence Ledger 中可审计的模型输出、判分和偏差信号。",
            ),
            _metric_card(
                "报告",
                "已生成" if report is not None else "等待生成",
                _root_cause_line(report) if report is not None else "任务完成后会生成结构化报告。",
            ),
        ]
        body = "\n".join(
            [
                _hero(
                    eyebrow="小D 用户视图",
                    title="Debug 任务详情",
                    subtitle=(
                        f"样本 {job.case_id} · 任务 {job.job_id}。这里展示用户需要判断的"
                        "进度、报告、证据和下一步，结构化 API 放在页面底部。"
                    ),
                    actions=[
                        _button("打开报告", report_url, "primary"),
                        _button(
                            "查看运行阶段",
                            self._view_url(f"/xiaod/views/jobs/{job_id}/run-stages"),
                        ),
                        _button(
                            "查看证据链",
                            self._view_url(f"/xiaod/views/jobs/{job_id}/evidence-ledger"),
                        ),
                    ],
                ),
                _cards(primary),
                _section(
                    "用户下一步",
                    _next_step_html(job=job, report=report),
                ),
                _section(
                    "关键阶段",
                    _stage_timeline_html(stages[:6], compact=True)
                    or _empty_state("还没有可展示的运行阶段。"),
                ),
                _section(
                    "相关入口",
                    _button_row(
                        [
                            _button(
                                "推荐动作",
                                self._view_url(
                                    f"/xiaod/views/jobs/{job_id}/recommended-actions"
                                ),
                            ),
                            _button(
                                "人工复核",
                                self._view_url(f"/xiaod/views/jobs/{job_id}/human-handoffs"),
                            ),
                            _button(
                                "所属批次",
                                self._view_url(
                                    f"/xiaod/views/debug-batches/{job.artifact_group_id}"
                                ),
                            ),
                        ]
                    ),
                ),
                _api_footer(
                    [
                        ("任务 JSON", self._absolute_url(f"/jobs/{job_id}")),
                        ("报告 JSON", self._absolute_url(f"/jobs/{job_id}/report")),
                    ]
                ),
            ]
        )
        return _page("Debug 任务详情", body)

    def report_view(self, job_id: str) -> str:
        job = self._require_job(job_id)
        report = self._build_report(job_id)
        document = self._job_repository.get_lark_report_document(job_id)
        if report is None:
            body = "\n".join(
                [
                    _hero(
                        eyebrow="小D 用户视图",
                        title="报告还没有生成",
                        subtitle=(
                            f"任务 {job.job_id} 当前状态为 {job.status}。任务完成并完成自动闭环后，"
                            "这里会展示结论、证据链和下一步建议。"
                        ),
                        actions=[
                            _button(
                                "查看任务进度",
                                self._view_url(f"/xiaod/views/jobs/{job_id}"),
                                "primary",
                            )
                        ],
                    ),
                    _api_footer([("报告 JSON", self._absolute_url(f"/jobs/{job_id}/report"))]),
                ]
            )
            return _page("Debug 报告未生成", body)
        report_actions = [
            _button("查看任务", self._view_url(f"/xiaod/views/jobs/{job_id}")),
            _button("证据链", self._view_url(f"/xiaod/views/jobs/{job_id}/evidence-ledger")),
        ]
        if document is not None and document.status == "published" and document.document_url:
            report_actions.insert(0, _button("打开飞书云文档", document.document_url, "primary"))
        body = "\n".join(
            [
                _hero(
                    eyebrow="最终报告",
                    title=f"{report.case_id} Debug 报告",
                    subtitle="先看结论、可信度和下一步，再进入证据链核对。",
                    actions=report_actions,
                ),
                _cards(
                    [
                        _metric_card(
                            "最终判断",
                            _text(_root_cause_label(report)),
                            _root_cause_line(report),
                        ),
                        _metric_card(
                            "失败现象",
                            _text(getattr(report.observed_failure, "type", "unknown")),
                            getattr(report.observed_failure, "summary", "") or "未记录失败摘要。",
                        ),
                        _metric_card(
                            "写回建议",
                            "先复核再写回",
                            "报告页面只展示建议；写回仍需要用户显式确认。",
                        ),
                    ]
                ),
                _section("推荐动作", _recommended_actions_html(report)),
                _section("证据摘要", _report_evidence_summary_html(report)),
                _section("结构化差异", _paragraph(report.suggested_sheet_fields.get("结构化差异", "无"))),
                _api_footer([("报告 JSON", self._absolute_url(f"/jobs/{job_id}/report"))]),
            ]
        )
        return _page(f"{report.case_id} Debug 报告", body)

    def run_stages_view(self, job_id: str) -> str:
        job = self._require_job(job_id)
        stages = self._job_repository.list_debug_run_stages(job_id)
        body = "\n".join(
            [
                _hero(
                    eyebrow="运行阶段",
                    title="Debug 运行时间线",
                    subtitle=f"任务 {job.job_id} · {len(stages)} 个阶段。每个阶段先展示结论，原始输入输出折叠在明细里。",
                    actions=[_button("返回任务", self._view_url(f"/xiaod/views/jobs/{job_id}"))],
                ),
                _section(
                    "阶段时间线",
                    _stage_timeline_html(stages, compact=False)
                    or _empty_state("还没有可展示的运行阶段。"),
                ),
                _api_footer([("运行阶段 JSON", self._absolute_url(f"/jobs/{job_id}/run-stages"))]),
            ]
        )
        return _page("Debug 运行阶段", body)

    def evidence_ledger_view(self, job_id: str) -> str:
        job = self._require_job(job_id)
        evidence = self._job_repository.list_evidence(job_id)
        body = "\n".join(
            [
                _hero(
                    eyebrow="证据链",
                    title="Evidence Ledger",
                    subtitle=(
                        f"任务 {job.job_id} · {len(evidence)} 条证据。这里优先解释每条证据"
                        "说明了什么，而不是直接展开原始 JSON。"
                    ),
                    actions=[_button("返回任务", self._view_url(f"/xiaod/views/jobs/{job_id}"))],
                ),
                _section(
                    "证据卡片",
                    _evidence_cards_html(evidence)
                    or _empty_state("当前任务还没有 evidence ledger 记录。"),
                ),
                _api_footer(
                    [("证据链 JSON", self._absolute_url(f"/jobs/{job_id}/evidence-ledger"))]
                ),
            ]
        )
        return _page("Evidence Ledger", body)

    def recommended_actions_view(self, job_id: str) -> str:
        self._require_job(job_id)
        report = self._build_report(job_id)
        statuses = self._job_repository.list_recommended_action_statuses(job_id)
        events = self._job_repository.list_recommended_action_status_events(job_id)
        verifications = self._job_repository.list_recommended_action_verifications(job_id)
        body = "\n".join(
            [
                _hero(
                    eyebrow="推荐动作",
                    title="推荐动作与验证状态",
                    subtitle="这里展示建议做什么、是否已确认、是否有验证任务。真正执行仍走显式按钮或接口。",
                    actions=[_button("返回任务", self._view_url(f"/xiaod/views/jobs/{job_id}"))],
                ),
                _section(
                    "动作清单",
                    _recommended_actions_html(report, statuses=statuses, verifications=verifications),
                ),
                _section("状态事件", _status_events_html(events)),
                _api_footer(
                    [
                        (
                            "推荐动作 JSON",
                            self._absolute_url(f"/jobs/{job_id}/recommended-actions/statuses"),
                        )
                    ]
                ),
            ]
        )
        return _page("推荐动作", body)

    def human_handoffs_view(self, job_id: str) -> str:
        self._require_job(job_id)
        report = self._build_report(job_id)
        statuses = self._job_repository.list_human_handoff_statuses(job_id)
        body = "\n".join(
            [
                _hero(
                    eyebrow="人工复核",
                    title="人工复核项",
                    subtitle="自动闭环无法直接证明的点会沉淀在这里，方便人接手判断。",
                    actions=[_button("返回任务", self._view_url(f"/xiaod/views/jobs/{job_id}"))],
                ),
                _section("复核清单", _human_handoffs_html(report, statuses)),
                _api_footer(
                    [
                        (
                            "人工复核 JSON",
                            self._absolute_url(f"/jobs/{job_id}/human-handoffs/statuses"),
                        )
                    ]
                ),
            ]
        )
        return _page("人工复核", body)

    def batch_view(self, batch_id: str) -> str:
        progress = self._build_batch_progress(batch_id)
        jobs = progress.recent_jobs
        body = "\n".join(
            [
                _hero(
                    eyebrow="批次",
                    title="Debug 批次概览",
                    subtitle=f"批次 {batch_id} · {progress.progress_percent}% 完成。",
                    actions=[_button("批次 JSON", self._absolute_url(f"/debug-batches/{batch_id}"))],
                ),
                _cards(
                    [
                        _metric_card("总任务", str(progress.batch.total_jobs), "本批次计划处理的任务数。"),
                        _metric_card("已完成", str(progress.completed_count), "完成的 DebugJob。"),
                        _metric_card("失败", str(progress.failed_count), "失败任务需要进入任务页查看原因。"),
                    ]
                ),
                _section("运行质量", _batch_summary_html(progress)),
                _section("最近任务", _batch_jobs_html(jobs)),
                _api_footer([("批次 JSON", self._absolute_url(f"/debug-batches/{batch_id}"))]),
            ]
        )
        return _page("Debug 批次概览", body)

    def manual_view(self) -> str:
        knowledge_dir = Path(__file__).resolve().parents[1] / "assistant" / "knowledge"
        documents = []
        for path in sorted(knowledge_dir.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            title = next(
                (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
                path.stem,
            )
            section_count = sum(1 for line in lines if line.startswith("## "))
            documents.append(
                {
                    "title": title,
                    "file": path.name,
                    "line_count": len(lines),
                    "section_count": section_count,
                    "preview": _clip(" ".join(line for line in lines[1:18] if line.strip()), 260),
                }
            )
        cards = [
            _metric_card("知识文档", str(len(documents)), "每份文档不低于 500 行，支撑小D问答和验收。"),
            _metric_card(
                "使用入口",
                "飞书卡片",
                "首次使用卡片只展示摘要，完整手册通过按钮打开。",
            ),
            _metric_card(
                "RAG索引",
                "向量 + 关键词",
                "文档会被切块并写入 SQLite 向量索引，问答返回 citation。",
            ),
        ]
        body = "\n".join(
            [
                _hero(
                    eyebrow="小D 使用手册",
                    title="Debug Agent 企业级落地手册",
                    subtitle=(
                        "这里汇总项目定位、用户使用、交互规则、debug流程、报告阅读、"
                        "卡片规范、运维上线和RAG自优化知识。"
                    ),
                    actions=[
                        _button("提交 badcase", "#submit-badcase", "primary"),
                        _button("表格重跑", "#spreadsheet-rerun"),
                        _button("报告阅读", "#report-reading"),
                        _button("RAG知识库", "#rag-learning"),
                    ],
                ),
                _cards(cards),
                _manual_section(
                    "submit-badcase",
                    "如何提交 badcase",
                    [
                        "发送原始输入、模型输出、正确答案和错误现象。",
                        "小D先保存草稿，字段齐全后发送确认卡片。",
                        "确认前不会创建 DebugJob；缺字段时会追问具体缺口。",
                    ],
                ),
                _manual_section(
                    "spreadsheet-rerun",
                    "表格重跑",
                    [
                        "发送飞书表格链接并说明行号、报告要求和写回偏好。",
                        "小D解析为 pending command，确认后创建批次。",
                        "source row mapping 决定报告覆盖和写回目标，probe job 不污染源行。",
                    ],
                ),
                _manual_section(
                    "report-reading",
                    "报告怎么看",
                    [
                        "先看最终报告卡片和云文档入口。",
                        "首屏判断结论、可信度、探索路线、已弱化假设和缺失证据。",
                        "证据不足时报告会标注 stopped_evidence_exhausted 或 inconclusive。",
                    ],
                ),
                _manual_section(
                    "operations",
                    "权限和上线",
                    [
                        "真实上线前必须通过 readiness、preflight 和 go-live gate。",
                        "飞书写操作、任务创建和表格写回都需要确认和审计。",
                        "outbox 失败要区分可重试错误和终态错误。",
                    ],
                ),
                _manual_section(
                    "rag-learning",
                    "RAG知识库和自优化",
                    [
                        "静态知识来自手册文档，动态经验来自 DebugLesson。",
                        "向量索引默认使用 local-hash-v1，生产可替换企业 embedding。",
                        "历史经验只能增强假设和解释，不能替代当前证据。",
                    ],
                ),
                _section("知识文档清单", _manual_documents_html(documents)),
            ]
        )
        return _page("小D Debug Agent 使用手册", body)

    def _require_job(self, job_id: str) -> DebugJobRow:
        job = self._job_repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        return job

    def _absolute_url(self, path: str) -> str:
        return f"{self._report_base_url().rstrip('/')}{path}"

    def _view_url(self, path: str) -> str:
        return self._absolute_url(path)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #172033;
      --muted: #667085;
      --line: #dfe5f2;
      --primary: #245bdb;
      --primary-soft: #eaf0ff;
      --green: #168a53;
      --yellow: #b7791f;
      --red: #c24141;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #eef4ff, var(--bg) 42%);
      color: var(--text);
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero, .section, .metric, .item {{
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 32px rgba(22, 32, 51, 0.06);
    }}
    .hero {{ padding: 28px; margin-bottom: 18px; }}
    .eyebrow {{
      color: var(--primary);
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 8px 0 10px; font-size: 30px; line-height: 1.2; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; }}
    p {{ line-height: 1.7; }}
    .subtitle, .muted {{ color: var(--muted); }}
    .actions, .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .button {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--text);
      text-decoration: none;
      background: #fff;
      font-weight: 650;
    }}
    .button.primary {{
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin: 18px 0;
    }}
    .metric {{ padding: 18px; }}
    .metric .label {{ color: var(--muted); font-size: 13px; }}
    .metric .value {{ margin: 8px 0; font-size: 24px; font-weight: 760; }}
    .section {{ padding: 22px; margin-top: 18px; }}
    .list {{ display: grid; gap: 12px; }}
    .item {{ padding: 16px; box-shadow: none; }}
    .pill {{
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--primary-soft);
      color: var(--primary);
      font-size: 12px;
      font-weight: 760;
    }}
    .pill.green {{ background: #eaf7f0; color: var(--green); }}
    .pill.yellow {{ background: #fff7e6; color: var(--yellow); }}
    .pill.red {{ background: #ffecec; color: var(--red); }}
    code, pre {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      background: #f4f6fb;
      border-radius: 8px;
    }}
    code {{ padding: 2px 5px; }}
    pre {{ overflow: auto; padding: 12px; }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; color: var(--primary); font-weight: 650; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 12px;
    }}
    th, td {{
      text-align: left;
      padding: 11px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-size: 13px; }}
    footer {{ margin-top: 24px; color: var(--muted); font-size: 13px; }}
  </style>
</head>
<body>
  <main>{body}</main>
</body>
</html>"""


def _hero(*, eyebrow: str, title: str, subtitle: str, actions: list[str]) -> str:
    return (
        '<section class="hero">'
        f'<div class="eyebrow">{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1>"
        f'<p class="subtitle">{escape(subtitle)}</p>'
        f'<div class="actions">{"".join(actions)}</div>'
        "</section>"
    )


def _section(title: str, content: str) -> str:
    return f'<section class="section"><h2>{escape(title)}</h2>{content}</section>'


def _manual_section(anchor: str, title: str, bullets: list[str]) -> str:
    items = "".join(f"<li>{escape(item)}</li>" for item in bullets)
    return (
        f'<section class="section" id="{escape(anchor, quote=True)}">'
        f"<h2>{escape(title)}</h2><ul>{items}</ul></section>"
    )


def _cards(cards: list[str]) -> str:
    return f'<div class="grid">{"".join(cards)}</div>'


def _metric_card(label: str, value: str, detail: str) -> str:
    return (
        '<article class="metric">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{value}</div>'
        f'<div class="muted">{escape(detail)}</div>'
        "</article>"
    )


def _button(label: str, url: str, style: str = "") -> str:
    klass = "button primary" if style == "primary" else "button"
    return f'<a class="{klass}" href="{escape(url, quote=True)}">{escape(label)}</a>'


def _button_row(buttons: list[str]) -> str:
    return f'<div class="button-row">{"".join(buttons)}</div>'


def _paragraph(value: str) -> str:
    return f"<p>{escape(value or '无')}</p>"


def _empty_state(value: str) -> str:
    return f'<p class="muted">{escape(value)}</p>'


def _api_footer(links: list[tuple[str, str]]) -> str:
    items = " · ".join(
        f'<a href="{escape(url, quote=True)}">{escape(label)}</a>' for label, url in links
    )
    return f"<footer>结构化 API：{items}</footer>"


def _status_pill(status: str) -> str:
    klass = "green" if status == "completed" else "red" if status == "failed" else "yellow"
    return f'<span class="pill {klass}">{escape(status or "unknown")}</span>'


def _text(value: object) -> str:
    return escape(str(value or "未知"))


def _root_cause_label(report: object | None) -> str:
    root_cause = getattr(report, "root_cause", None)
    if root_cause is None:
        return "报告未生成"
    label = getattr(root_cause, "label", "unknown")
    confidence = getattr(root_cause, "confidence", "unknown")
    return f"{label} / {confidence}"


def _root_cause_line(report: object | None) -> str:
    root_cause = getattr(report, "root_cause", None)
    if root_cause is None:
        return "报告未生成。"
    return str(getattr(root_cause, "evidence_summary", "") or "报告暂未给出证据摘要。")


def _next_step_html(*, job: DebugJobRow, report: object | None) -> str:
    actions = getattr(report, "recommended_actions", []) if report is not None else []
    if actions:
        first = actions[0]
        if isinstance(first, dict):
            summary = str(first.get("summary", "查看推荐动作。"))
            priority = str(first.get("priority", "P0"))
            return _paragraph(f"{priority}：{summary}")
    if job.status == "completed":
        return _paragraph("先打开报告核对结论和证据链，再决定是否写回。")
    if job.status == "failed":
        return _paragraph(job.error_message or "任务失败，但未记录失败原因。")
    return _paragraph("等待任务继续运行；小D会在大阶段变化时推送进度。")


def _stage_timeline_html(stages: list[DebugRunStage], *, compact: bool) -> str:
    if not stages:
        return ""
    items: list[str] = []
    for stage in stages:
        summary = _stage_summary(stage)
        details = "" if compact else _details_json("阶段输入/输出", stage.model_dump(mode="json"))
        items.append(
            '<article class="item">'
            f"<h3>{escape(stage.stage)} {_status_pill(stage.status)}</h3>"
            f'<p class="muted">更新于 {escape(stage.updated_at or stage.created_at)}</p>'
            f"<p>{escape(summary)}</p>"
            f"{details}"
            "</article>"
        )
    return f'<div class="list">{"".join(items)}</div>'


def _stage_summary(stage: DebugRunStage) -> str:
    if stage.failure_reason:
        return stage.failure_reason
    output = stage.output if isinstance(stage.output, dict) else {}
    for key in ("summary", "status_label", "phase", "decision", "next_action"):
        value = output.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    debug_loop = output.get("debug_loop")
    if isinstance(debug_loop, dict):
        decision = str(debug_loop.get("decision", "")).strip()
        iteration = str(debug_loop.get("current_iteration", "")).strip()
        if decision:
            return f"自动探索第 {iteration or '?'} 轮：{decision}。"
    return "阶段已记录，展开明细可查看结构化输入输出。"


def _evidence_cards_html(evidence_items: list[ExperimentEvidence]) -> str:
    items: list[str] = []
    for evidence in evidence_items:
        deltas = _evidence_deltas(evidence)
        errors = evidence.model_call_error_message or evidence.response_parse_error
        signal = errors or deltas or "本条证据未暴露结构化偏差。"
        value = (
            "这条证据说明链路本身有运行异常，需要先排除调用或解析问题。"
            if errors
            else "这条证据用于判断原问题是否复现，或验证补充约束是否真的改善结果。"
        )
        items.append(
            '<article class="item">'
            f"<h3>{escape(evidence.evidence_id)} {_status_pill(str(evidence.judge.score))}</h3>"
            f'<p class="muted">{escape(evidence.step_name)} · trial {evidence.trial}</p>'
            f"<p><strong>关键观察：</strong>{escape(signal)}</p>"
            f"<p><strong>归因价值：</strong>{escape(value)}</p>"
            f"<p><strong>原始输出摘要：</strong>{escape(_clip(evidence.raw_output, 260))}</p>"
            f"{_details_json('证据结构化明细', evidence.model_dump(mode='json'))}"
            "</article>"
        )
    return f'<div class="list">{"".join(items)}</div>' if items else ""


def _evidence_deltas(evidence: ExperimentEvidence) -> str:
    values: list[str] = []
    for delta in evidence.judge.deltas:
        reason = str(delta.get("reason", "")).strip()
        if reason:
            values.append(reason)
    values.extend(str(reason) for reason in evidence.judge.reasons if str(reason).strip())
    return "，".join(dict.fromkeys(values))


def _recommended_actions_html(
    report: object | None,
    *,
    statuses: list[object] | None = None,
    verifications: list[object] | None = None,
) -> str:
    actions = getattr(report, "recommended_actions", []) if report is not None else []
    statuses_by_index = {
        int(getattr(status, "action_index", -1)): status for status in (statuses or [])
    }
    verification_counts: dict[int, int] = {}
    for verification in verifications or []:
        index = int(getattr(verification, "action_index", -1))
        verification_counts[index] = verification_counts.get(index, 0) + 1
    if not actions:
        return _empty_state("当前报告没有可直接执行的推荐动作。")
    items: list[str] = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        status = statuses_by_index.get(index)
        state = getattr(status, "status", action.get("status", "pending"))
        summary = str(action.get("summary", "未填写动作摘要"))
        detail = str(action.get("detail", "") or "")
        priority = str(action.get("priority", f"P{index}"))
        verify_count = verification_counts.get(index, 0)
        detail_html = (
            f'<p class="muted">{escape(detail)}</p>' if detail and detail != summary else ""
        )
        items.append(
            '<article class="item">'
            f"<h3>{escape(priority)} {_status_pill(str(state))}</h3>"
            f"<p>{escape(summary)}</p>"
            f"{detail_html}"
            f'<p class="muted">验证任务：{verify_count} 个</p>'
            "</article>"
        )
    return f'<div class="list">{"".join(items)}</div>' if items else _empty_state("没有推荐动作。")


def _status_events_html(events: list[object]) -> str:
    if not events:
        return _empty_state("还没有状态事件。")
    rows = [
        "<tr><th>动作</th><th>状态</th><th>操作者</th><th>说明</th><th>时间</th></tr>"
    ]
    for event in events:
        rows.append(
            "<tr>"
            f"<td>{escape(str(getattr(event, 'action_index', '')))}</td>"
            f"<td>{_status_pill(str(getattr(event, 'status', '')))}</td>"
            f"<td>{escape(str(getattr(event, 'actor', '')))}</td>"
            f"<td>{escape(str(getattr(event, 'note', '')))}</td>"
            f"<td>{escape(str(getattr(event, 'created_at', '')))}</td>"
            "</tr>"
        )
    return f"<table>{''.join(rows)}</table>"


def _human_handoffs_html(report: object | None, statuses: list[object]) -> str:
    requests = getattr(report, "human_handoff_requests", []) if report is not None else []
    statuses_by_target = {str(getattr(status, "target_id", "")): status for status in statuses}
    if not requests and not statuses:
        return _empty_state("当前没有人工复核项。")
    items: list[str] = []
    for index, request in enumerate(requests or [], start=1):
        if not isinstance(request, dict):
            continue
        target_id = str(request.get("target_id", f"handoff-{index}"))
        status = statuses_by_target.get(target_id)
        state = getattr(status, "status", request.get("status", "pending"))
        summary = str(request.get("summary", request.get("reason", "需要人工复核。")))
        items.append(
            '<article class="item">'
            f"<h3>{escape(target_id)} {_status_pill(str(state))}</h3>"
            f"<p>{escape(summary)}</p>"
            "</article>"
        )
    for status in statuses:
        target_id = str(getattr(status, "target_id", ""))
        if any(isinstance(item, dict) and item.get("target_id") == target_id for item in requests):
            continue
        items.append(
            '<article class="item">'
            f"<h3>{escape(target_id)} {_status_pill(str(getattr(status, 'status', '')))}</h3>"
            f"<p>{escape(str(getattr(status, 'note', '') or '已记录人工复核状态。'))}</p>"
            "</article>"
        )
    return f'<div class="list">{"".join(items)}</div>'


def _report_evidence_summary_html(report: object) -> str:
    citations = getattr(report, "evidence_citations", []) or []
    if citations:
        items = []
        for citation in citations[:5]:
            if isinstance(citation, dict):
                evidence_id = str(citation.get("evidence_id", ""))
                summary = str(citation.get("summary", citation.get("reason", "")))
                items.append(f"<li><code>{escape(evidence_id)}</code>：{escape(summary)}</li>")
        return f"<ul>{''.join(items)}</ul>" if items else _empty_state("没有证据摘要。")
    experiment_summary = getattr(report, "experiment_summary", None)
    if experiment_summary is None:
        return _empty_state("报告没有实验摘要。")
    return _paragraph(
        f"共 {experiment_summary.total_trials} 次实验，成功 {experiment_summary.success_count} 次，"
        f"稳定性 {experiment_summary.stability_label}。"
    )


def _batch_summary_html(progress: DebugBatchProgressResponse) -> str:
    summary = progress.evaluation_summary
    return (
        "<p>"
        f"成功率 {summary.success_rate:.2%}，P95 {summary.p95_duration_ms}ms，"
        f"稳定性 {escape(summary.stability_label)}，可信度 {escape(summary.trust_label)}。"
        "</p>"
    )


def _batch_jobs_html(jobs: list[DebugJobStatus]) -> str:
    if not jobs:
        return _empty_state("当前批次还没有最近任务。")
    rows = ["<tr><th>任务</th><th>样本</th><th>状态</th><th>入口</th></tr>"]
    for job in jobs:
        rows.append(
            "<tr>"
            f"<td><code>{escape(job.job_id)}</code></td>"
            f"<td>{escape(job.case_id)}</td>"
            f"<td>{_status_pill(job.status)}</td>"
            f"<td><a href=\"/xiaod/views/jobs/{escape(job.job_id, quote=True)}\">打开</a></td>"
            "</tr>"
        )
    return f"<table>{''.join(rows)}</table>"


def _manual_documents_html(documents: list[dict[str, object]]) -> str:
    if not documents:
        return _empty_state("知识库目录还没有 Markdown 手册。")
    rows = ["<tr><th>文档</th><th>行数</th><th>章节</th><th>摘要</th></tr>"]
    for document in documents:
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(document['file']))}</code><br>{escape(str(document['title']))}</td>"
            f"<td>{escape(str(document['line_count']))}</td>"
            f"<td>{escape(str(document['section_count']))}</td>"
            f"<td>{escape(str(document['preview']))}</td>"
            "</tr>"
        )
    return f"<table>{''.join(rows)}</table>"


def _details_json(label: str, payload: object) -> str:
    return (
        f"<details><summary>{escape(label)}</summary>"
        f"<pre>{escape(json.dumps(payload, ensure_ascii=False, indent=2, default=str))}</pre>"
        "</details>"
    )


def _clip(value: str, limit: int) -> str:
    normalized = " ".join(str(value).split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."

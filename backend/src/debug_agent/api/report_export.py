from __future__ import annotations

from debug_agent.reports.generator import DebugReport
from debug_agent.storage.models import DebugJobRow


def build_html_report(*, job: DebugJobRow, report: DebugReport | None) -> bytes:
    if report is None:
        html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Debug Job - {_html_escape(job.job_id)}</title>
</head>
<body>
  <h1>Debug Job Summary</h1>
  <p><strong>Job:</strong> {_html_escape(job.job_id)}</p>
  <p><strong>Case:</strong> {_html_escape(job.case_id)}</p>
  <p><strong>Status:</strong> {_html_escape(job.status)}</p>
  <p>该任务还没有可生成的完整归因报告；ZIP 中仍包含任务状态、run stages、evidence 和审计数据。</p>
</body>
</html>"""
        return html.encode("utf-8")
    evidence_items = "".join(
        f"<li><code>{_html_escape(_report_item_value(citation, 'evidence_id'))}</code> - "
        f"{_html_escape(_report_item_value(citation, 'reason'))}</li>"
        for citation in (report.evidence_citations or [])
    )
    actions = "".join(
        f"<li><strong>{_html_escape(_report_item_value(action, 'priority'))}</strong> "
        f"{_html_escape(_report_item_value(action, 'summary'))}"
        f"<p>{_html_escape(_report_item_value(action, 'detail'))}</p></li>"
        for action in (report.recommended_actions or [])
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Debug Report - {_html_escape(job.job_id)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 32px auto; line-height: 1.6; color: #172033; }}
    code {{ background: #eef2ff; padding: 2px 5px; border-radius: 4px; }}
    section {{ border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 16px; }}
  </style>
</head>
<body>
  <h1>Debug Report</h1>
  <p><strong>Job:</strong> {_html_escape(job.job_id)}</p>
  <p><strong>Case:</strong> {_html_escape(job.case_id)}</p>
  <p><strong>Status:</strong> {_html_escape(job.status)}</p>
  <section>
    <h2>Observed Failure</h2>
    <p>{_html_escape(report.observed_failure.summary)}</p>
  </section>
  <section>
    <h2>Root Cause</h2>
    <p><strong>{_html_escape(report.root_cause.label)}</strong> / {_html_escape(report.root_cause.confidence)}</p>
    <p>{_html_escape(report.root_cause.evidence_summary)}</p>
  </section>
  <section>
    <h2>Evidence</h2>
    <ul>{evidence_items or "<li>无</li>"}</ul>
  </section>
  <section>
    <h2>Recommended Actions</h2>
    <ul>{actions or "<li>无</li>"}</ul>
  </section>
</body>
</html>"""
    return html.encode("utf-8")


def _html_escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _report_item_value(item: object, key: str) -> object:
    if isinstance(item, dict):
        return item.get(key, "")
    return getattr(item, key, "")

from debug_agent.reports.lark_docx_renderer import build_lark_docx_report_xml


def test_lark_docx_renderer_adds_reading_aids_without_dropping_report_sections() -> None:
    markdown = """# JSZN-131 最终 Debug 报告

## 第一层：一页看懂

- 根因：模型时序输出不稳定 / 高置信。
- 自动写回状态：`not_requested`。

## 结论先行

- 原始 vs Live：baseline 0/3；targeted 1/1。

## 第二层：证据链

## 原始 Badcase 证据

### 原模型预测

```json
{"answer":"3"}
```

## 证据明细

### 证据地图

| 阶段 | 证据数 |
| --- | --- |
| baseline_replay | 1 条 |

## 输入与 Prompt 改动审计

原始 prompt 保持不变。

## 第三层：审计附录

## 阶段方法解释

- **Baseline 复测**：按原始条件复测。
"""

    xml = build_lark_docx_report_xml(case_id="JSZN-131", source_markdown=markdown)

    assert "<title>JSZN-131 最终 Debug 报告</title>" in xml
    assert "<h2>第一层：一页看懂</h2>" in xml
    assert "<h2>原始 Badcase 证据</h2>" in xml
    assert "<h2>输入与 Prompt 改动审计</h2>" in xml
    assert "<h2>阶段方法解释</h2>" in xml
    assert '<callout emoji="✅" background-color="light-green"' in xml
    assert "<p><b>先看这三件事</b></p>" in xml
    assert "<grid>" in xml
    assert "<p><b>证据链阅读顺序</b></p>" in xml
    assert (
        "<p><b>本区读法：</b>按“证据地图 → 关键证据卡片 → 证据解读 → "
        "原始输出索引”的顺序看。正文只保留关键原始输出摘要。</p>"
    ) in xml
    assert (
        "<p><b>审计说明：</b>这一层用于追溯输入、Prompt 改动和 Agent "
        "可见输入输出摘要。它不改变前文结论。</p>"
    ) in xml
    assert '<pre lang="json" caption="原始报告片段"><code>{"answer":"3"}</code></pre>' in xml
    assert '<th background-color="light-gray">阶段</th>' in xml
    assert "<td>baseline_replay</td>" in xml
    assert "<h3>先看这三件事</h3>" not in xml
    assert "<h3>证据链阅读顺序</h3>" not in xml
    assert "report_presentation_agent" not in xml
    assert "版式计划审计" not in xml
    assert "完整报告正文" not in xml


def test_lark_docx_renderer_escapes_source_markdown_text() -> None:
    markdown = """# escaping

## 第一层：一页看懂

- 原始输出：`<bad&value>`。
- 粗体：**<should escape>**。
"""

    xml = build_lark_docx_report_xml(case_id="case-1", source_markdown=markdown)

    assert "<title>escaping</title>" in xml
    assert "<code>&lt;bad&amp;value&gt;</code>" in xml
    assert "<b>&lt;should escape&gt;</b>" in xml
    assert "<bad&value>" not in xml
    assert "<should escape>" not in xml

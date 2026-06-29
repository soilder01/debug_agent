from html import escape
import re


def build_lark_docx_report_xml(*, case_id: str, source_markdown: str) -> str:
    """Render the markdown report as Lark Docx XML with deterministic reading aids."""
    title, body_markdown = _extract_title(case_id=case_id, markdown=source_markdown)
    return "\n".join(
        [
            f"<title>{_x(title)}</title>",
            "",
            *_markdown_to_lark_xml_blocks(body_markdown),
        ]
    )


def _extract_title(*, case_id: str, markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            title = match.group(1).strip()
            body = "\n".join([*lines[:index], *lines[index + 1 :]]).strip()
            return title, body
    return f"{case_id} 最终 Debug 报告", markdown


def _markdown_to_lark_xml_blocks(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    ordered_items: list[str] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    code_lang = "text"

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(item.strip() for item in paragraph if item.strip())
            if text:
                blocks.append(f"<p>{_inline_xml(text)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>")
            blocks.extend(f"<li>{_inline_xml(item)}</li>" for item in list_items)
            blocks.append("</ul>")
            list_items.clear()
        if ordered_items:
            blocks.append("<ol>")
            blocks.extend(f'<li seq="auto">{_inline_xml(item)}</li>' for item in ordered_items)
            blocks.append("</ol>")
            ordered_items.clear()

    def flush_table() -> None:
        if table_lines:
            blocks.extend(_markdown_table_to_xml(table_lines))
            table_lines.clear()

    def flush_code() -> None:
        if code_lines:
            code = "\n".join(code_lines)
            blocks.append(
                f'<pre lang="{_x_attr(code_lang)}" caption="原始报告片段"><code>{_x(code)}</code></pre>'
            )
            code_lines.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
                code_lang = "text"
            else:
                flush_paragraph()
                flush_list()
                flush_table()
                in_code = True
                code_lang = stripped.strip("`").strip() or "text"
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if re.fullmatch(r"(-{3,}|_{3,}|\*{3,})", stripped):
            flush_paragraph()
            flush_list()
            flush_table()
            blocks.append("<hr/>")
            continue
        if _is_table_line(stripped):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 4)
            title = heading.group(2).strip()
            blocks.append(f"<h{level}>{_inline_xml(title)}</h{level}>")
            blocks.extend(_reading_aid_blocks(title))
            continue
        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        if unordered:
            flush_paragraph()
            ordered_items.clear()
            list_items.append(unordered.group(1))
            continue
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            list_items.clear()
            ordered_items.append(ordered.group(1))
            continue
        paragraph.append(stripped)

    flush_code()
    flush_paragraph()
    flush_list()
    flush_table()
    return blocks


def _reading_aid_blocks(title: str) -> list[str]:
    if title == "第一层：一页看懂":
        return [
            '<callout emoji="✅" background-color="light-green" border-color="green" text-color="green">',
            "<p><b>先看这三件事</b></p>",
            "<ul>",
            "<li><b>结论：</b>先确认根因、最终归因和写回状态。</li>",
            "<li><b>证据：</b>先看 Action Queue 和证据地图，再进入原始 Badcase 与审计附录。</li>",
            "<li><b>下一步：</b>确认推荐动作后再执行写回。</li>",
            "</ul>",
            "</callout>",
            "<grid>",
            '<column width-ratio="0.33">',
            "<p><b>结论层</b></p>",
            "<p>用一页看懂、调试过程一览和结论先行快速判断本次调试是否可信。</p>",
            "</column>",
            '<column width-ratio="0.34">',
            "<p><b>证据层</b></p>",
            "<p>用原始 Badcase、自动深挖、证据地图和结构化差异核对根因来源。</p>",
            "</column>",
            '<column width-ratio="0.33">',
            "<p><b>审计层</b></p>",
            "<p>用 Prompt 改动和 Agent 输入输出摘要复盘调试链路，不参与改写结论。</p>",
            "</column>",
            "</grid>",
            "<hr/>",
        ]
    if title in {"结论先行", "结论与处理建议"}:
        return [
            '<callout emoji="📌" background-color="light-blue" border-color="blue" text-color="blue">',
            "<p><b>读法：</b>这一节是报告的决策入口。先确认根因、最终归因、原始 vs Live 复测和写回状态。</p>",
            "</callout>",
        ]
    if title == "第二层：证据链":
        return [
            '<callout emoji="🔎" background-color="light-yellow" border-color="yellow" text-color="yellow">',
            "<p><b>证据链阅读顺序</b></p>",
            "<ol>",
            '<li seq="auto">先看原始 Badcase，确认原始输出和参考答案的差异。</li>',
            '<li seq="auto">再看自动深挖链路，确认 baseline、targeted、verification 是否形成闭环。</li>',
            '<li seq="auto">最后看证据明细和结构化差异，核对每条 evidence 对根因的贡献。</li>',
            "</ol>",
            "</callout>",
        ]
    if title == "证据明细":
        return [
            '<callout emoji="🧭" background-color="light-blue" border-color="blue" text-color="blue">',
            "<p><b>本区读法：</b>按“证据地图 → 关键证据卡片 → 证据解读 → 原始输出索引”的顺序看。正文只保留关键原始输出摘要。</p>",
            "</callout>",
        ]
    if title == "第三层：审计附录":
        return [
            '<callout emoji="📝" background-color="light-gray" border-color="gray">',
            "<p><b>审计说明：</b>这一层用于追溯输入、Prompt 改动和 Agent 可见输入输出摘要。它不改变前文结论。</p>",
            "</callout>",
        ]
    return []


def _is_table_line(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _markdown_table_to_xml(lines: list[str]) -> list[str]:
    rows = [_split_table_row(line) for line in lines if not _is_table_separator(line)]
    if not rows:
        return []
    header = rows[0]
    body = rows[1:]
    output = ["<table>", "<thead><tr>"]
    output.extend(f'<th background-color="light-gray">{_inline_xml(cell)}</th>' for cell in header)
    output.extend(["</tr></thead>", "<tbody>"])
    for row in body:
        output.append("<tr>")
        padded = row + [""] * max(0, len(header) - len(row))
        output.extend(f"<td>{_inline_xml(cell)}</td>" for cell in padded[: len(header)])
        output.append("</tr>")
    output.extend(["</tbody>", "</table>"])
    return output


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells)


def _inline_xml(value: str) -> str:
    placeholders: list[str] = []

    def stash(fragment: str) -> str:
        placeholders.append(fragment)
        return f"@@INLINE_{len(placeholders) - 1}@@"

    text = str(value)
    text = re.sub(r"`([^`]+)`", lambda match: stash(f"<code>{_x(match.group(1))}</code>"), text)
    escaped = _x(text)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    for index, fragment in enumerate(placeholders):
        escaped = escaped.replace(f"@@INLINE_{index}@@", fragment)
    return escaped


def _x(value: str) -> str:
    return escape(str(value), quote=False)


def _x_attr(value: str) -> str:
    return escape(str(value), quote=True)

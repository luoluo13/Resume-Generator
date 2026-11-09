from __future__ import annotations

import io
import re
from collections import Counter

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.importers.base import Block, ImportParseError, ParseResult, clean_line

DEFAULT_SIZE = 10.5
SERIF_HINTS = ("song", "serif", "ming", "楷", "宋", "仿宋", "明朝")


def _run_font_name(run) -> str:
    name = run.font.name or ""
    if name:
        return name
    rpr = run._element.rPr
    if rpr is not None and rpr.rFonts is not None:
        return rpr.rFonts.get(qn("w:eastAsia")) or rpr.rFonts.get(qn("w:ascii")) or ""
    return ""


def _run_size(run) -> float:
    size = run.font.size
    return size.pt if size is not None else 0.0


def _run_bold(run) -> bool:
    if run.bold:
        return True
    style = run.style
    return bool(style is not None and style.font.bold)


def _paragraph_metrics(paragraph: Paragraph, fallback: float) -> tuple[str, float, bool]:
    text = clean_line(paragraph.text)
    runs = [run for run in paragraph.runs if run.text]
    sizes = [_run_size(run) for run in runs if _run_size(run)]
    if sizes:
        size = max(sizes)
    else:
        style_size = paragraph.style.font.size if paragraph.style is not None else None
        size = style_size.pt if style_size is not None else fallback
    if runs:
        total = sum(len(run.text) for run in runs) or 1
        bold_chars = sum(len(run.text) for run in runs if _run_bold(run))
        bold = bold_chars / total >= 0.6
    else:
        bold = bool(paragraph.style is not None and paragraph.style.font.bold)
    return text, size, bold


def _iter_block_items(parent):
    if isinstance(parent, DocumentObject):
        parent_element = parent.element.body
    else:
        parent_element = parent._tc
    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _append_block(blocks: list[Block], text: str, size: float, bold: bool, *, table: bool = False) -> None:
    text = clean_line(text)
    if not text:
        return
    if blocks and blocks[-1].text == text and blocks[-1].table == table:
        return
    blocks.append(Block(text=text, size=size or DEFAULT_SIZE, bold=bold, table=table))


def parse_docx(raw: bytes) -> ParseResult:
    try:
        document = Document(io.BytesIO(raw))
    except Exception as exc:
        raise ImportParseError("无法读取 DOCX 文件，请确认文件没有损坏或加密。") from exc

    normal_size = DEFAULT_SIZE
    try:
        if document.styles["Normal"].font.size is not None:
            normal_size = document.styles["Normal"].font.size.pt
    except KeyError:
        pass

    blocks: list[Block] = []
    warnings: list[str] = []
    has_table = False

    for section in document.sections:
        for paragraph in section.header.paragraphs:
            text, size, bold = _paragraph_metrics(paragraph, normal_size)
            _append_block(blocks, text, size, bold)

    for item in _iter_block_items(document):
        if isinstance(item, Paragraph):
            text, size, bold = _paragraph_metrics(item, normal_size)
            _append_block(blocks, text, size, bold)
            continue
        has_table = True
        seen_cells: set[int] = set()
        for row in item.rows:
            for cell in row.cells:
                marker = id(cell._tc)
                if marker in seen_cells:
                    continue
                seen_cells.add(marker)
                for paragraph in cell.paragraphs:
                    text, size, bold = _paragraph_metrics(paragraph, normal_size)
                    _append_block(blocks, text, size, bold, table=True)

    for section in document.sections:
        for paragraph in section.footer.paragraphs:
            text, size, bold = _paragraph_metrics(paragraph, normal_size)
            if re.fullmatch(r"[-—\s]*\d{1,3}[-—\s]*", text):
                continue
            _append_block(blocks, text, size, bold)

    for block in blocks:
        block.page = 1

    if not blocks:
        raise ImportParseError("文档中没有可读取的文字内容，若为扫描件请先转换为可复制的文字。")

    if has_table:
        warnings.append("检测到表格排版，已按单元格顺序提取文字，请核对模块与条目顺序。")
    xml = document.element.xml
    if "txbxContent" in xml:
        warnings.append("检测到文本框内容，DOCX 文本框中的文字可能未被完整读取，请重点校对。")

    font_names: list[str] = []
    colors: Counter[str] = Counter()
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            name = _run_font_name(run)
            if name and run.text:
                font_names.append(name)
            color = run.font.color
            if color is not None and color.rgb is not None and run.text:
                hex_value = str(color.rgb).upper()
                if _is_accent(hex_value):
                    colors[hex_value] += len(run.text)

    serif = False
    if font_names:
        serif_hits = sum(1 for name in font_names if any(hint in name.lower() for hint in SERIF_HINTS))
        serif = serif_hits / len(font_names) >= 0.3

    accent = ""
    if colors:
        accent = f"#{colors.most_common(1)[0][0]}"

    has_images = bool(document.inline_shapes) or "<pic:pic" in xml
    return ParseResult(
        blocks=blocks,
        warnings=warnings,
        pages=1,
        has_images=has_images,
        columns_hint=1,
        serif=serif,
        accent=accent,
    )


def _is_accent(hex_value: str) -> bool:
    if not re.fullmatch(r"[0-9A-F]{6}", hex_value):
        return False
    red, green, blue = (int(hex_value[index : index + 2], 16) for index in (0, 2, 4))
    high, low = max(red, green, blue), min(red, green, blue)
    if high < 60 or high > 245:
        return False
    return high - low >= 35

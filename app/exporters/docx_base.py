from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.models import plain_text
from app.services.fonts import docx_font_details

SECTION_EN = {
    "education": "EDUCATION",
    "experience": "EXPERIENCE",
    "project": "PROJECTS",
    "skills": "SKILLS",
    "awards": "HONORS",
    "certificate": "CERTIFICATES",
}


def hex_rgb(value: str) -> RGBColor:
    value = value.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


@dataclass
class Ctx:
    body_font: str
    head_font: str
    font_size: float
    line_spacing: float
    gap: float
    accent: RGBColor
    accent_hex: str
    ink: RGBColor
    muted: RGBColor
    usable_cm: float


def set_run(
    run,
    font: str,
    size: float,
    *,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor | None = None,
    underline: bool = False,
) -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if underline:
        run.font.underline = True
    if color is not None:
        run.font.color.rgb = color
    rfonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), font)


def shade_run(run, color_hex: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex.lstrip("#"))
    run._element.get_or_add_rPr().append(shd)


def shade_cell(cell, color_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex.lstrip("#"))
    tc_pr.append(shd)


def remove_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "none")
        element.set(qn("w:sz"), "0")
        borders.append(element)
    tbl_pr.append(borders)


def set_table_layout(table, widths_cm: tuple[float, ...]) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for index, width in enumerate(widths_cm):
        table.columns[index].width = Cm(width)
    for row in table.rows:
        for index, width in enumerate(widths_cm):
            row.cells[index].width = Cm(width)


def set_cell_margins(table, top: int = 0, bottom: int = 0, left: int = 0, right: int = 0) -> None:
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        mar.append(element)
    tbl_pr.append(mar)


def paragraph_border(paragraph, color_hex: str, edge: str = "bottom", size: int = 6, space: int = 2) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    element = OxmlElement(f"w:{edge}")
    element.set(qn("w:val"), "single")
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:space"), str(space))
    element.set(qn("w:color"), color_hex.lstrip("#"))
    p_bdr.append(element)


def style_paragraph(paragraph, ctx: Ctx, *, before: float = 0, after: float = 0, dense: bool = False) -> None:
    fmt = paragraph.paragraph_format
    fmt.line_spacing = Pt(ctx.font_size * ctx.line_spacing * 1.2)
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after * (0.72 if dense else 1.0))


def add_rich(paragraph, markup: str, ctx: Ctx, size: float, *, color: RGBColor | None = None) -> None:
    bold = italic = link = False
    pending_space = False
    for token in re.split(r"(<[^>]*>)", markup or ""):
        if not token:
            continue
        if token.startswith("<"):
            low = token.lower()
            name_match = re.match(r"</?\s*([a-z0-9]+)", low)
            if not name_match:
                continue
            name = name_match.group(1)
            closing = low.startswith("</")
            if name in ("strong", "b"):
                bold = not closing
            elif name in ("em", "i"):
                italic = not closing
            elif name == "a":
                link = not closing
            elif name == "br" or (name == "p" and closing):
                pending_space = True
            continue
        text = re.sub(r"[ \t\r\n]+", " ", html.unescape(token))
        if not paragraph.runs:
            text = text.lstrip()
        if not text.strip():
            continue
        if pending_space and paragraph.runs:
            text = " " + text.lstrip()
        pending_space = False
        run = paragraph.add_run(text)
        set_run(
            run,
            ctx.body_font,
            size,
            bold=bold,
            italic=italic,
            color=ctx.accent if link else color,
            underline=link,
        )


def contact_line(basics: dict) -> str:
    parts = [
        basics.get("phone", ""),
        basics.get("email", ""),
        basics.get("city", ""),
        f"{basics['available']}到岗" if basics.get("available") else "",
        f"{basics['yearsOfExperience']}经验" if basics.get("yearsOfExperience") else "",
        basics.get("gender", ""),
        f"{basics['birth']}出生" if basics.get("birth") else "",
        basics.get("political", ""),
    ]
    return "  ·  ".join(part for part in parts if part)


def date_text(item: dict) -> str:
    if not (item.get("start") or item.get("end") or item.get("current")):
        return ""
    end = "至今" if item.get("current") else item.get("end", "")
    if item.get("start") and end:
        return f'{item["start"]} – {end}'
    return item.get("start") or end


def add_header_text(container, resume: dict, ctx: Ctx, profile: dict, *, color: RGBColor | None = None) -> None:
    basics = resume["basics"]
    centered = profile.get("layout") == "centered"
    align = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT

    name_p = container.add_paragraph()
    name_p.alignment = align
    style_paragraph(name_p, ctx, after=ctx.font_size * 0.18)
    run = name_p.add_run(basics.get("name") or "")
    set_run(run, ctx.head_font, ctx.font_size * 2.15, bold=True, color=color or ctx.ink)

    if basics.get("jobIntention"):
        intent_p = container.add_paragraph()
        intent_p.alignment = align
        style_paragraph(intent_p, ctx, after=ctx.font_size * 0.18)
        run = intent_p.add_run(basics["jobIntention"])
        set_run(run, ctx.body_font, ctx.font_size * 0.94, bold=not centered, color=color or ctx.accent)

    contacts = contact_line(basics)
    if contacts:
        contact_p = container.add_paragraph()
        contact_p.alignment = align
        style_paragraph(contact_p, ctx, after=ctx.font_size * 0.55)
        run = contact_p.add_run(contacts)
        muted = RGBColor(255, 255, 255) if color else ctx.muted
        set_run(run, ctx.body_font, ctx.font_size * 0.75, color=muted)


def add_header(doc: DocxDocument, resume: dict, ctx: Ctx, profile: dict, photo: Path | None) -> None:
    layout = profile.get("layout", "single")
    if layout == "band":
        table = doc.add_table(rows=1, cols=2)
        remove_table_borders(table)
        set_table_layout(table, (ctx.usable_cm - 3.0, 3.0))
        set_cell_margins(table, top=140, bottom=140, left=180, right=120)
        band_color = profile.get("band_color") or "1E1C18"
        if band_color == "accent":
            band_color = ctx.accent_hex
        for cell in table.rows[0].cells:
            shade_cell(cell, band_color)
        white = RGBColor(255, 255, 255)
        left = table.rows[0].cells[0]
        left.paragraphs[0].text = ""
        add_header_text(left, resume, ctx, profile, color=white)
        if photo and profile.get("photo", True):
            right = table.rows[0].cells[1]
            right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            right.paragraphs[0].add_run().add_picture(str(photo), width=Cm(2.1))
        return

    if layout == "centered":
        add_header_text(doc, resume, ctx, profile)
        if photo and profile.get("photo", True):
            photo_p = doc.add_paragraph()
            photo_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            style_paragraph(photo_p, ctx, after=ctx.font_size * 0.2)
            photo_p.add_run().add_picture(str(photo), width=Cm(2.0))
        rule = doc.add_paragraph()
        style_paragraph(rule, ctx, after=ctx.font_size * 0.2)
        paragraph_border(rule, ctx.accent_hex, size=10, space=1)
        return

    if photo and profile.get("photo", True):
        table = doc.add_table(rows=1, cols=2)
        remove_table_borders(table)
        set_table_layout(table, (ctx.usable_cm - 3.2, 3.2))
        set_cell_margins(table)
        left = table.rows[0].cells[0]
        add_header_text(left, resume, ctx, profile)
        right = table.rows[0].cells[1]
        right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        right.paragraphs[0].add_run().add_picture(str(photo), width=Cm(2.2))
        rule_p = doc.add_paragraph()
        style_paragraph(rule_p, ctx, after=ctx.font_size * 0.5)
        paragraph_border(rule_p, ctx.accent_hex, size=8)
        return

    add_header_text(doc, resume, ctx, profile)
    rule_p = doc.add_paragraph()
    style_paragraph(rule_p, ctx, after=ctx.font_size * 0.5)
    paragraph_border(rule_p, ctx.accent_hex, size=8)


def add_section_title(container, title: str, index: int | None, ctx: Ctx, profile: dict, en: str = "") -> None:
    style = profile.get("section_style", "rule")
    paragraph = container.add_paragraph()
    style_paragraph(paragraph, ctx, before=ctx.font_size * 1.25 * ctx.gap, after=ctx.font_size * 0.45,
                    dense=profile.get("dense", False))
    paragraph.paragraph_format.keep_with_next = True
    if style == "centered":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    prefix = f"{index:02d}  " if profile.get("numbered") and index else ""
    label = f"{prefix}{title}"
    if profile.get("section_en") and en:
        label = f"{label}  {en}"

    if style == "badge":
        run = paragraph.add_run(f" {label} ")
        set_run(run, ctx.head_font, ctx.font_size * 0.92, bold=True, color=RGBColor(255, 255, 255))
        shade_run(run, ctx.accent_hex)
    else:
        color = ctx.accent if style in ("rule", "bar") else ctx.ink
        run = paragraph.add_run(label)
        set_run(run, ctx.head_font, ctx.font_size * 0.98, bold=True, color=color)

    if style == "rule":
        paragraph_border(paragraph, ctx.accent_hex, size=4)
    elif style == "bar":
        paragraph.paragraph_format.left_indent = Cm(0.18)
        paragraph_border(paragraph, ctx.accent_hex, edge="left", size=18, space=4)
    elif style == "centered":
        paragraph_border(paragraph, "DED8CB", size=4)
    elif style == "boxed":
        paragraph_border(paragraph, "E0DACE", edge="top", size=4)
        paragraph_border(paragraph, "E0DACE", edge="bottom", size=4)


def add_bullet(container, markup: str, ctx: Ctx, profile: dict) -> None:
    text = plain_text(markup)
    if not text:
        return
    paragraph = container.add_paragraph()
    style_paragraph(paragraph, ctx, after=ctx.font_size * 0.12, dense=profile.get("dense", False))
    paragraph.paragraph_format.left_indent = Cm(0.42)
    add_rich(paragraph, markup, ctx, ctx.font_size * 0.8)


def add_entry_heading(container, left_markup: str, right: str, ctx: Ctx, profile: dict) -> None:
    paragraph = container.add_paragraph()
    style_paragraph(paragraph, ctx, after=ctx.font_size * 0.1, dense=profile.get("dense", False))
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(ctx.usable_cm), WD_TAB_ALIGNMENT.RIGHT)
    add_rich(paragraph, left_markup, ctx, ctx.font_size * 0.9)
    if right:
        run = paragraph.add_run(f"\t{right}")
        set_run(run, ctx.body_font, ctx.font_size * 0.72, color=ctx.muted)


def add_meta(container, text: str, ctx: Ctx, profile: dict) -> None:
    if not text:
        return
    paragraph = container.add_paragraph()
    style_paragraph(paragraph, ctx, after=ctx.font_size * 0.08, dense=profile.get("dense", False))
    run = paragraph.add_run(text)
    set_run(run, ctx.body_font, ctx.font_size * 0.73, color=ctx.muted)


def render_items(container, section: dict, ctx: Ctx, profile: dict) -> None:
    kind = section["type"]
    for item in section.get("items", []):
        if kind == "education":
            left = item.get("school", "")
            meta = " · ".join(part for part in (item.get("degree"), item.get("major")) if part)
            if meta:
                left += f"  {meta}"
            add_entry_heading(container, left, date_text(item), ctx, profile)
            notes = []
            if item.get("gpa"):
                notes.append(f'GPA {item["gpa"]}')
            if item.get("courses"):
                notes.append(item["courses"])
            add_meta(container, " · ".join(notes), ctx, profile)
        elif kind in ("experience", "project"):
            primary = item.get("company") or item.get("name")
            secondary = item.get("role") or ""
            left = f"{primary}  {secondary}".strip()
            if item.get("location") and kind == "experience":
                left += f"  {item['location']}"
            add_entry_heading(container, left, date_text(item), ctx, profile)
            if item.get("tech"):
                add_meta(container, " / ".join(item["tech"]), ctx, profile)
            for highlight in item.get("highlights", []):
                add_bullet(container, highlight, ctx, profile)
            if item.get("link"):
                add_meta(container, item["link"], ctx, profile)
        elif kind == "skills":
            paragraph = container.add_paragraph()
            style_paragraph(paragraph, ctx, after=ctx.font_size * 0.12, dense=profile.get("dense", False))
            run = paragraph.add_run(f'{item.get("group", "")}  ')
            set_run(run, ctx.body_font, ctx.font_size * 0.8, bold=True, color=ctx.ink)
            run = paragraph.add_run("、".join(item.get("tags", [])))
            set_run(run, ctx.body_font, ctx.font_size * 0.8, color=ctx.ink)
        elif kind in ("awards", "certificate"):
            left = item.get("name", "")
            if item.get("issuer"):
                left += f"  {item['issuer']}"
            add_entry_heading(container, left, item.get("date", ""), ctx, profile)
        else:
            title = item.get("title") or ""
            if title or item.get("subtitle"):
                left = f"{title}  {item.get('subtitle', '')}".strip()
                add_entry_heading(container, left, date_text(item), ctx, profile)
            for highlight in item.get("highlights", []):
                add_bullet(container, highlight, ctx, profile)


def render_sections(container, sections: list[dict], ctx: Ctx, profile: dict, *, start_index: int = 1) -> None:
    index = start_index
    for section in sections:
        add_section_title(container, section.get("title", ""), index, ctx, profile, SECTION_EN.get(section["type"], ""))
        render_items(container, section, ctx, profile)
        index += 1


def render_sidebar(doc: DocxDocument, resume: dict, ctx: Ctx, profile: dict) -> None:
    sidebar_types = set(profile.get("sidebar_types", ()))
    main_sections = [s for s in resume["sections"] if s["visible"] and s["type"] not in sidebar_types]
    side_sections = [s for s in resume["sections"] if s["visible"] and s["type"] in sidebar_types]
    side_cm = ctx.usable_cm * 0.36
    main_cm = ctx.usable_cm - side_cm - 0.35

    table = doc.add_table(rows=1, cols=2)
    remove_table_borders(table)
    set_table_layout(table, (side_cm, main_cm))
    set_cell_margins(table, top=120, bottom=120, left=120, right=120)
    side_cell, main_cell = table.rows[0].cells
    shade_cell(side_cell, "F7F2E6")
    side_cell.paragraphs[0].text = ""

    basics = resume["basics"]
    name_p = side_cell.add_paragraph()
    style_paragraph(name_p, ctx, after=ctx.font_size * 0.2)
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = name_p.add_run(basics.get("name") or "")
    set_run(run, ctx.head_font, ctx.font_size * 1.7, bold=True, color=ctx.ink)
    if basics.get("jobIntention"):
        intent_p = side_cell.add_paragraph()
        intent_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_paragraph(intent_p, ctx, after=ctx.font_size * 0.4)
        run = intent_p.add_run(basics["jobIntention"])
        set_run(run, ctx.body_font, ctx.font_size * 0.8, bold=True, color=ctx.accent)
    contacts = contact_line(basics)
    if contacts:
        for line in contacts.split("  ·  "):
            contact_p = side_cell.add_paragraph()
            style_paragraph(contact_p, ctx, after=ctx.font_size * 0.12)
            run = contact_p.add_run(line)
            set_run(run, ctx.body_font, ctx.font_size * 0.72, color=ctx.muted)

    side_profile = dict(profile)
    side_profile["section_style"] = "rule"
    render_sections(side_cell, side_sections, ctx, side_profile, start_index=len(main_sections) + 1)

    main_cell.paragraphs[0].text = ""
    main_profile = dict(profile)
    main_profile["section_style"] = "plain"
    render_sections(main_cell, main_sections, ctx, main_profile)


def render_timeline(doc: DocxDocument, resume: dict, ctx: Ctx, profile: dict) -> None:
    index = 1
    for section in resume["sections"]:
        if not section["visible"]:
            continue
        add_section_title(doc, section.get("title", ""), index, ctx, profile)
        index += 1
        for item in section.get("items", []):
            kind = section["type"]
            date = ""
            if kind in ("education", "experience", "project", "custom"):
                date = date_text(item)
            elif kind in ("awards", "certificate"):
                date = item.get("date", "")
            table = doc.add_table(rows=1, cols=2)
            remove_table_borders(table)
            set_table_layout(table, (2.6, ctx.usable_cm - 2.6))
            set_cell_margins(table)
            date_cell, body_cell = table.rows[0].cells
            date_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            date_run = date_cell.paragraphs[0].add_run(date)
            set_run(date_run, ctx.body_font, ctx.font_size * 0.7, color=ctx.muted)
            paragraph = body_cell.paragraphs[0]
            style_paragraph(paragraph, ctx, after=ctx.font_size * 0.1, dense=profile.get("dense", False))
            paragraph.paragraph_format.keep_with_next = True
            if kind == "education":
                title = item.get("school", "")
                sub = " · ".join(part for part in (item.get("degree"), item.get("major")) if part)
            elif kind in ("experience", "project"):
                title = item.get("company") or item.get("name", "")
                sub = item.get("role", "")
            elif kind == "skills":
                title = item.get("group", "")
                sub = "、".join(item.get("tags", []))
            else:
                title = item.get("name") or item.get("title", "")
                sub = item.get("issuer", "")
            run = paragraph.add_run(title)
            set_run(run, ctx.body_font, ctx.font_size * 0.88, bold=True, color=ctx.ink)
            if sub:
                run = paragraph.add_run(f"  {sub}")
                set_run(run, ctx.body_font, ctx.font_size * 0.78, color=ctx.muted)
            if kind in ("education", "experience", "project", "custom"):
                for highlight in item.get("highlights", []):
                    add_bullet(body_cell, highlight, ctx, profile)


def build_document(resume: dict, theme: dict, profile: dict, photo: Path | None = None) -> DocxDocument:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    margin = Cm(theme["pageMargin"] / 10)
    section.top_margin = margin
    section.bottom_margin = margin
    section.left_margin = margin
    section.right_margin = margin
    section.header_distance = Cm(0)
    section.footer_distance = Cm(0)

    body_font, serif_font = docx_font_details(theme["fontFamily"])
    font_size = float(theme["fontSize"])
    normal = doc.styles["Normal"]
    normal.font.name = body_font
    normal.font.size = Pt(font_size)
    rfonts = normal.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), body_font)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    gap = {"compact": 0.68, "normal": 1.0, "loose": 1.3}[theme["density"]]
    head_font = serif_font if profile.get("serif") else body_font
    ctx = Ctx(
        body_font=body_font,
        head_font=head_font,
        font_size=font_size,
        line_spacing=float(theme["lineHeight"]),
        gap=gap,
        accent=hex_rgb(theme["accent"]),
        accent_hex=theme["accent"],
        ink=RGBColor(0x23, 0x21, 0x1C),
        muted=RGBColor(0x7F, 0x78, 0x6C),
        usable_cm=21 - theme["pageMargin"] / 10 * 2,
    )

    layout = profile.get("layout", "single")
    if layout == "sidebar":
        render_sidebar(doc, resume, ctx, profile)
        return doc

    add_header(doc, resume, ctx, profile, photo if theme.get("photoPosition") != "none" else None)
    visible = [s for s in resume["sections"] if s["visible"]]
    if layout == "timeline":
        render_timeline(doc, resume, ctx, profile)
    else:
        render_sections(doc, visible, ctx, profile)
    return doc

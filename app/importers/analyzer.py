from __future__ import annotations

import re
from pathlib import Path
from statistics import median
from typing import Any

from app.importers.base import (
    Block,
    ImportParseError,
    ParseResult,
    SECTION_TITLES,
    SINGLE_DATE_RE,
    clean_line,
    detect_name,
    extract_basics,
    find_period,
    is_basics_line,
    is_bullet,
    is_contact_line,
    match_heading,
    match_heading_block,
    normalize_key,
    remove_period,
    split_tags,
    strip_bullet,
)
from app.importers.doc_importer import convert_doc
from app.importers.docx_importer import parse_docx
from app.importers.pdf_importer import parse_pdf

ALLOWED_SUFFIXES = {".docx": "docx", ".pdf": "pdf", ".doc": "doc"}


def analyze_document(raw: bytes, filename: str, registry) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    kind = ALLOWED_SUFFIXES.get(suffix)
    if kind is None:
        raise ImportParseError("仅支持 DOC、DOCX、PDF 三种格式。")
    if not raw:
        raise ImportParseError("文件内容为空。")

    payload = convert_doc(raw) if kind == "doc" else raw
    parsed = parse_pdf(payload) if kind == "pdf" else parse_docx(payload)
    return assemble_draft(parsed, filename, kind, registry)


def _new_item(headline: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    return {
        "headline": clean_line(headline),
        "meta": "",
        "period": "",
        "bullets": [],
        "tags": tags or [],
    }


def _period_text(info: tuple[str, str, bool]) -> str:
    start, end, current = info
    if current:
        return f"{start} - 至今"
    if end:
        return f"{start} - {end}"
    return start


def _has_content(item: dict[str, Any]) -> bool:
    return bool(item["headline"] or item["meta"] or item["period"] or item["bullets"] or item["tags"])


def _build_entries(blocks: list[Block], body_size: float) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for block in blocks:
        text = block.stripped()
        if not text:
            continue
        if is_bullet(text):
            bullet = strip_bullet(text)
            if not bullet:
                continue
            if current is None:
                current = _new_item()
                items.append(current)
            current["bullets"].append(bullet)
            continue

        info = find_period(text)
        remainder = remove_period(text) if info else text
        heading_like = bool(info) or (block.bold and block.size >= body_size - 0.1 and len(text) <= 42)

        if info and not remainder and current is not None and not current["period"]:
            current["period"] = _period_text(info)
            continue

        if heading_like:
            if (
                current is not None
                and info
                and not current["period"]
                and not current["meta"]
                and not current["bullets"]
            ):
                current["meta"] = remainder
                current["period"] = _period_text(info)
                continue
            if current is None or (current["period"] and (current["bullets"] or current["meta"])):
                current = _new_item()
                items.append(current)
            if not current["headline"]:
                current["headline"] = remainder
            elif not current["meta"]:
                current["meta"] = remainder
            else:
                current["bullets"].append(remainder)
            if info:
                current["period"] = _period_text(info)
            continue

        if current is None:
            current = _new_item()
            items.append(current)
        if not current["headline"]:
            current["headline"] = text
        elif not current["meta"] and len(text) <= 40 and not current["bullets"]:
            current["meta"] = text
        else:
            current["bullets"].append(text)

    return [item for item in items if _has_content(item) and (item["headline"] or item["bullets"])]


def _build_skills(blocks: list[Block]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in blocks:
        text = strip_bullet(block.stripped()) if is_bullet(block.stripped()) else block.stripped()
        if not text:
            continue
        parts = re.split(r"[:：]", text, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and len(parts[0].strip()) <= 16:
            group = parts[0].strip()
            tags = split_tags(parts[1])
        else:
            tags = split_tags(text)
            group = "" if len(tags) >= 2 else text
            if len(tags) < 2:
                tags = []
        if group or tags:
            items.append(_new_item(group, tags))
    return items


def _build_awards(blocks: list[Block]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in blocks:
        text = strip_bullet(block.stripped()) if is_bullet(block.stripped()) else block.stripped()
        if not text:
            continue
        info = find_period(text)
        name = remove_period(text) if info else text
        period = _period_text(info) if info else ""
        if not period:
            single = SINGLE_DATE_RE.search(text)
            if single:
                period = single.group(0).strip()
                name = (text[: single.start()] + " " + text[single.end() :]).strip(" |｜·-–—:：")
        if not name:
            name = text
        items.append(_new_item(name))
        items[-1]["period"] = period
    return items


def _build_items(section_type: str, blocks: list[Block], body_size: float) -> list[dict[str, Any]]:
    if section_type == "skills":
        return _build_skills(blocks)
    if section_type in ("awards", "certificate"):
        return _build_awards(blocks)
    return _build_entries(blocks, body_size)


def assemble_draft(parsed: ParseResult, source_name: str, kind: str, registry) -> dict[str, Any]:
    blocks = [block for block in parsed.blocks if block.stripped()]
    if not blocks:
        raise ImportParseError("没有识别到可导入的文字内容。")

    sizes = [block.size for block in blocks if block.size > 0] or [10.5]
    body_size = float(median(sizes))
    basics = extract_basics(blocks)
    name = detect_name(blocks, body_size)
    basics["name"] = name

    content: list[Block] = []
    for block in blocks:
        text = block.stripped()
        if name and text == name:
            continue
        if is_contact_line(text):
            continue
        if is_basics_line(text):
            continue
        content.append(block)

    raw_sections: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    preface: list[Block] = []
    keyword_hits = 0

    for block in content:
        heading = match_heading_block(block, body_size)
        if heading:
            section_type, title = heading
            if match_heading(block.stripped()):
                keyword_hits += 1
            key = (section_type, normalize_key(title))
            if key in seen:
                current = seen[key]
            else:
                current = {
                    "type": section_type,
                    "title": title,
                    "confidence": 0.92 if match_heading(block.stripped()) else 0.64,
                    "blocks": [],
                }
                seen[key] = current
                raw_sections.append(current)
            continue
        if current is None:
            preface.append(block)
        else:
            current["blocks"].append(block)

    if preface:
        raw_sections.insert(
            0,
            {"type": "custom", "title": "个人概述", "confidence": 0.55, "blocks": preface},
        )

    sections: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_sections):
        items = _build_items(raw["type"], raw["blocks"], body_size)
        if not items:
            continue
        sections.append(
            {
                "id": f"import-sec-{index + 1}",
                "title": raw["title"][:20] or SECTION_TITLES[raw["type"]],
                "type": raw["type"],
                "confidence": raw["confidence"],
                "items": items[:120],
            }
        )

    if not sections:
        raise ImportParseError("未能从文件中整理出可编辑的模块，请尝试另存为 DOCX 后重新导入。")

    total_items = sum(len(section["items"]) for section in sections)
    warnings = list(parsed.warnings)
    if not basics.get("name"):
        warnings.append("未能识别姓名，请在下一步补充。")
    if keyword_hits == 0:
        warnings.append("未找到常见的模块标题，已按内容顺序整理为自定义模块，请核对归类。")
    missing_period = sum(
        1
        for section in sections
        if section["type"] in ("education", "experience", "project")
        for item in section["items"]
        if not item["period"]
    )
    if missing_period:
        warnings.append(f"有 {missing_period} 条经历未识别到时间段，可在编辑器中补填。")
    if parsed.has_images:
        warnings.append("原文件包含图片，照片与图标不会导入，可在编辑器右上角重新上传照片。")

    stats = {
        "blocks": len(blocks),
        "characters": sum(len(block.stripped()) for block in blocks),
        "items": total_items,
        "entries": sum(
            len(section["items"]) for section in sections if section["type"] in ("education", "experience", "project")
        ),
        "maxSize": max(sizes),
        "bodySize": body_size,
    }
    style = recommend_style(parsed, stats, registry)
    return {
        "file": {
            "name": source_name,
            "kind": kind,
            "size": 0,
            "pages": parsed.pages,
        },
        "basics": {
            "name": basics.get("name", ""),
            "jobIntention": basics.get("jobIntention", ""),
            "phone": basics.get("phone", ""),
            "email": basics.get("email", ""),
            "city": basics.get("city", ""),
            "yearsOfExperience": basics.get("yearsOfExperience", ""),
            "available": basics.get("available", ""),
        },
        "sections": sections,
        "style": style,
        "warnings": warnings,
        "stats": stats,
    }


def recommend_style(parsed: ParseResult, stats: dict[str, Any], registry) -> dict[str, Any]:
    manifests = registry.list()
    by_id = {manifest["id"]: manifest for manifest in manifests}
    if not manifests:
        raise ImportParseError("未找到可用模板，请先在模板中心导入模板。")

    template_id = "classic" if "classic" in by_id else manifests[0]["id"]
    reason = "内容结构均衡，推荐单栏经典版式，最稳妥也最容易继续调整。"

    if parsed.columns_hint >= 2 and "balanced" in by_id:
        template_id = "balanced"
        reason = "检测到双栏排版，推荐「衡 · 双栏均衡」承接原来的信息分区。"
    elif parsed.serif and "academic" in by_id:
        template_id = "academic"
        reason = "原文以衬线字体为主，推荐「雅 · 衬线学术」，更接近原稿的阅读气质。"
    elif stats["blocks"] >= 60 and "compact" in by_id:
        template_id = "compact"
        reason = "原文内容较多，推荐「简 · 紧凑单页」，更容易控制页数。"
    elif stats["maxSize"] - stats["bodySize"] >= 6 and stats["blocks"] <= 45 and "minimal" in by_id:
        template_id = "minimal"
        reason = "原文姓名区字号较大、内容克制，推荐「白 · 极简留白」保留留白感。"
    elif stats["entries"] >= 5 and "timeline" in by_id:
        template_id = "timeline"
        reason = "经历条目较多且有明确时间线，推荐「序 · 时间轴」突出叙事顺序。"

    manifest = by_id[template_id]
    supports = manifest.get("supports") or {}
    columns_supported = supports.get("columns") or [1]
    dividers = supports.get("divider") or ["line", "none", "block"]
    columns = 2 if parsed.columns_hint >= 2 and 2 in columns_supported else columns_supported[0]

    accent = parsed.accent if re.fullmatch(r"#[0-9a-fA-F]{6}", parsed.accent or "") else manifest.get("color", "#bf4a2e")
    photo_position = "right" if parsed.has_images and supports.get("photo", True) else "none"

    theme = {
        "template": template_id,
        "accent": accent,
        "fontFamily": "SourceHanSerifSC" if parsed.serif else "SourceHanSansSC",
        "fontSize": 10.5,
        "lineHeight": 1.35,
        "pageMargin": 18,
        "columns": columns,
        "photoPosition": photo_position,
        "dividerStyle": dividers[0],
        "density": "compact" if stats["blocks"] >= 60 else "normal",
        "variants": {},
    }
    return {"template": template_id, "reason": reason, "theme": theme}

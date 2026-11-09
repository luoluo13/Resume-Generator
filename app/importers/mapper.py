from __future__ import annotations

import html
import re
from typing import Any

from app.importers.base import (
    DATE_RANGE_RE,
    SINGLE_DATE_RE,
    SECTION_TITLES,
    SECTION_TYPES,
    clean_line,
    find_period,
    split_tags,
)
from app.models import Resume, Theme

DEGREE_HINTS = ("博士", "硕士", "本科", "学士", "大专", "专科", "研究生", "高中", "中专", "MBA", "EMBA")
ROLE_HINTS = (
    "工程师",
    "经理",
    "主管",
    "总监",
    "专员",
    "开发",
    "设计",
    "负责人",
    "实习",
    "运营",
    "产品",
    "架构师",
    "分析师",
    "顾问",
    "研究员",
    "教师",
    "leader",
    "engineer",
    "manager",
    "developer",
)
FONT_OPTIONS = {"SourceHanSansSC", "SourceHanSerifSC", "MicrosoftYaHei"}


def _text(value: Any, limit: int = 0) -> str:
    if value is None:
        return ""
    text = clean_line(str(value))
    return text[:limit] if limit else text


def _rich(value: Any) -> str:
    text = _text(value)
    return html.escape(text, quote=False)


def _dedupe(values: list[str], limit: int = 24) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _period_parts(period: str) -> tuple[str, str, bool]:
    period = _text(period)
    if not period:
        return "", "", False
    info = find_period(period)
    if info:
        return info
    parts = re.split(r"\s*(?:-|–|—|~|～|至|到)\s*", period)
    if len(parts) == 2:
        start, end = parts[0].strip(), parts[1].strip()
        current = end.lower() in ("至今", "现在", "今", "present", "now")
        return start, "" if current else end, current
    return period, "", False


def _split_headline(headline: str, meta: str) -> tuple[str, str]:
    if meta:
        return headline, meta
    pieces = re.split(r"\s*[|｜]\s*", headline, maxsplit=1)
    if len(pieces) == 2 and pieces[1].strip():
        return pieces[0].strip(), pieces[1].strip()
    pieces = re.split(r"\s+", headline, maxsplit=1)
    if len(pieces) == 2 and any(hint in pieces[1].lower() for hint in ROLE_HINTS):
        return pieces[0].strip(), pieces[1].strip()
    return headline, meta


def _split_degree(meta: str) -> tuple[str, str]:
    if not meta:
        return "", ""
    parts = [part for part in re.split(r"[·•|｜/／,，\s]+", meta) if part.strip()]
    degree = ""
    major_parts: list[str] = []
    for part in parts:
        if not degree and any(hint in part for hint in DEGREE_HINTS):
            degree = part
        else:
            major_parts.append(part)
    if major_parts:
        return degree, " ".join(major_parts)
    return degree, "" if degree else meta


def _map_basics(raw: dict[str, Any]) -> dict[str, Any]:
    phone = re.sub(r"[^0-9+\-\s()]", "", _text(raw.get("phone"), 20))
    if not re.fullmatch(r"[0-9+\-\s()]{6,20}", phone):
        phone = ""
    email = _text(raw.get("email"), 120)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        email = ""
    return {
        "name": _text(raw.get("name"), 30),
        "jobIntention": _text(raw.get("jobIntention"), 30),
        "phone": phone,
        "email": email,
        "city": _text(raw.get("city"), 20),
        "available": _text(raw.get("available"), 20),
        "yearsOfExperience": _text(raw.get("yearsOfExperience"), 20),
        "gender": "",
        "birth": "",
        "political": "",
        "photo": "",
    }


def _map_item(section_type: str, raw: dict[str, Any]) -> dict[str, Any] | None:
    headline = _text(raw.get("headline"))
    meta = _text(raw.get("meta"))
    period = _text(raw.get("period"))
    bullets = [_rich(value) for value in raw.get("bullets") or [] if _text(value)]
    tags = [_text(value) for value in raw.get("tags") or [] if _text(value)]
    start, end, current = _period_parts(period)

    if section_type == "skills":
        group = headline
        all_tags = _dedupe(tags + split_tags(meta) + split_tags(" ".join(_text(value) for value in raw.get("bullets") or [])))
        if not group and not all_tags:
            return None
        return {"group": group, "tags": all_tags, "highlights": []}

    if section_type in ("awards", "certificate"):
        name = headline
        date = period
        if not date:
            single = SINGLE_DATE_RE.search(headline)
            if single:
                date = single.group(0).strip()
                name = (headline[: single.start()] + " " + headline[single.end() :]).strip(" |｜·-–—:：")
        if not (name or date or meta):
            return None
        return {"name": name, "issuer": meta, "date": date}

    if section_type == "education":
        school = headline
        if not meta:
            degree_match = re.search(r"(博士|硕士|本科|学士|大专|专科|研究生|MBA|EMBA)", headline)
            if degree_match and degree_match.start() > 0:
                school = headline[: degree_match.start()].strip()
                meta = headline[degree_match.start() :].strip()
        degree, major = _split_degree(meta)
        if not (headline or meta or bullets):
            return None
        return {
            "school": school,
            "degree": degree,
            "major": major,
            "start": start,
            "end": end,
            "current": current,
            "highlights": bullets,
        }

    if section_type == "experience":
        if not (headline or meta or bullets):
            return None
        headline, meta = _split_headline(headline, meta)
        return {
            "company": headline,
            "role": meta,
            "start": start,
            "end": end,
            "current": current,
            "highlights": bullets,
        }

    if section_type == "project":
        if not (headline or meta or bullets):
            return None
        headline, meta = _split_headline(headline, meta)
        return {
            "name": headline,
            "role": meta,
            "start": start,
            "end": end,
            "current": current,
            "highlights": bullets,
        }

    if not (headline or meta or bullets or period):
        return None
    return {
        "title": headline,
        "subtitle": meta,
        "start": start,
        "end": end,
        "current": current,
        "highlights": bullets,
    }


def _map_section(raw: dict[str, Any], index: int) -> dict[str, Any] | None:
    section_type = str(raw.get("type") or "custom")
    if section_type not in SECTION_TYPES:
        section_type = "custom"
    title = _text(raw.get("title"), 20) or SECTION_TITLES[section_type]
    items: list[dict[str, Any]] = []
    for entry in raw.get("items") or []:
        if not isinstance(entry, dict):
            continue
        item = _map_item(section_type, entry)
        if item:
            items.append(item)
    if not items:
        return None
    return {
        "id": f"import_{index + 1}_{section_type}",
        "type": section_type,
        "title": title,
        "visible": True,
        "items": items[:150],
    }


def _clamp(value: Any, low: float, high: float, fallback: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return fallback


def _resolve_theme(raw: dict[str, Any], registry) -> dict[str, Any]:
    manifests = registry.list()
    by_id = {manifest["id"]: manifest for manifest in manifests}
    template = str(raw.get("template") or "")
    if template not in by_id:
        template = "classic" if "classic" in by_id else manifests[0]["id"]
    manifest = by_id[template]
    supports = manifest.get("supports") or {}
    columns = supports.get("columns") or [1]
    dividers = supports.get("divider") or ["line", "none", "block"]

    accent = str(raw.get("accent") or "")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        accent = str(manifest.get("color") or "#bf4a2e")
    font = str(raw.get("fontFamily") or "")
    if font not in FONT_OPTIONS:
        font = "SourceHanSansSC"

    photo = str(raw.get("photoPosition") or "none")
    if not supports.get("photo", True):
        photo = "none"
    elif photo not in ("none", "right", "left"):
        photo = "none"

    divider = str(raw.get("dividerStyle") or "")
    if divider not in dividers:
        divider = dividers[0]

    density = str(raw.get("density") or "normal")
    if density not in ("loose", "normal", "compact"):
        density = "normal"

    theme = {
        "template": template,
        "accent": accent,
        "fontFamily": font,
        "fontSize": _clamp(raw.get("fontSize"), 9, 12, 10.5),
        "lineHeight": _clamp(raw.get("lineHeight"), 1.0, 1.6, 1.35),
        "pageMargin": int(_clamp(raw.get("pageMargin"), 12, 25, 18)),
        "columns": int(raw.get("columns")) if raw.get("columns") in columns else columns[0],
        "photoPosition": photo,
        "dividerStyle": divider,
        "density": density,
        "variants": {},
    }
    return Theme.model_validate(theme).model_dump(mode="json")


def build_resume(payload: dict[str, Any], current: dict[str, Any], registry) -> dict[str, Any]:
    basics = _map_basics(payload.get("basics") if isinstance(payload.get("basics"), dict) else {})
    sections: list[dict[str, Any]] = []
    for index, raw in enumerate(payload.get("sections") or []):
        if not isinstance(raw, dict):
            continue
        section = _map_section(raw, index)
        if section:
            sections.append(section)
    if not sections:
        from app.importers.base import ImportParseError

        raise ImportParseError("没有可导入的模块内容，请返回上一步检查。")

    theme = _resolve_theme(payload.get("theme") if isinstance(payload.get("theme"), dict) else {}, registry)
    meta = dict(current.get("meta") or {})
    data = {
        "schemaVersion": 1,
        "id": current.get("id") or "default",
        "meta": meta,
        "basics": basics,
        "sections": sections,
        "theme": theme,
    }
    try:
        resume = Resume.model_validate(data)
    except Exception as exc:
        from app.importers.base import ImportParseError

        raise ImportParseError("导入内容未通过校验，请检查姓名、电话、邮箱以及模块标题。") from exc
    return resume.model_dump(mode="json")

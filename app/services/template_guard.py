from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MAX_MARKUP_BYTES = 160 * 1024
MAX_MANIFEST_BYTES = 24 * 1024
REQUIRED_FILES = ("manifest.json", "template.html", "style.css")

ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,31}$")
VARIANT_KEY_RE = re.compile(r"^[a-z][a-zA-Z0-9]{1,23}$")
VARIANT_VALUE_RE = re.compile(r"^[a-z][a-z0-9-]{0,23}$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

_HTML_RULES = (
    (re.compile(r"(?is)<\s*script\b"), "不允许使用 <script>"),
    (re.compile(r"(?is)<\s*(iframe|object|embed|form|base|link)\b"), "不允许引入外部或可执行元素"),
    (re.compile(r"(?is)<\s*meta[^>]+http-equiv"), "不允许使用 meta 跳转"),
    (re.compile(r"(?is)\bon[a-z]+\s*="), "不允许内联事件属性"),
    (re.compile(r"(?is)javascript\s*:"), "不允许 javascript: 链接"),
    (re.compile(r"""(?is)(?:src|href|xlink:href)\s*=\s*["']?\s*(?:https?:)?//"""), "不允许引用外部资源"),
    (re.compile(r"(?is)url\s*\(\s*['\"]?\s*(?:https?:)?//"), "不允许引用外部资源"),
    (re.compile(r"(?is)@import\b"), "不允许使用 @import"),
    (re.compile(r"(?is)(?:expression|-moz-binding)\s*\("), "不允许使用不安全的 CSS 表达式"),
    (re.compile(r"(?is)\{%-?\s*(extends|include|import|from)\b"), "模板必须单文件自包含，不允许 extends/include/import"),
)

_CSS_RULES = (
    (re.compile(r"(?is)@import\b"), "不允许使用 @import"),
    (re.compile(r"(?is)url\s*\(\s*['\"]?\s*(?:https?:)?//"), "不允许引用外部资源"),
    (re.compile(r"(?is)javascript\s*:"), "不允许 javascript: 链接"),
    (re.compile(r"(?is)(?:expression|-moz-binding)\s*\("), "不允许使用不安全的 CSS 表达式"),
)


class TemplateGuardError(Exception):
    pass


def check_markup(content: str, filename: str) -> None:
    rules = _HTML_RULES + _CSS_RULES if filename.endswith(".html") else _CSS_RULES
    for pattern, message in rules:
        if pattern.search(content):
            raise TemplateGuardError(f"{filename}：{message}")


def check_text_size(content: str, filename: str) -> None:
    if len(content.encode("utf-8")) > MAX_MARKUP_BYTES:
        raise TemplateGuardError(f"{filename} 超过 160KB，请精简样式")


def validate_manifest(data: Any) -> dict:
    if not isinstance(data, dict):
        raise TemplateGuardError("manifest.json 必须是 JSON 对象")

    template_id = str(data.get("id", "")).strip()
    if not ID_RE.fullmatch(template_id):
        raise TemplateGuardError("模板 id 只能使用 3~32 位小写字母、数字或连字符，且以字母开头")

    name = str(data.get("name", "")).strip()
    if not name or len(name) > 30:
        raise TemplateGuardError("模板名称不能为空，且不超过 30 个字")

    description = str(data.get("description", "")).strip()
    if len(description) > 200:
        raise TemplateGuardError("模板简介不能超过 200 个字")

    raw_tags = data.get("tags", [])
    if not isinstance(raw_tags, list):
        raise TemplateGuardError("tags 必须是数组")
    tags = [str(tag).strip()[:12] for tag in raw_tags if str(tag).strip()][:6]

    color = str(data.get("color", "#bf4a2e"))
    if not COLOR_RE.fullmatch(color):
        raise TemplateGuardError("color 必须是 #RRGGBB 格式")

    try:
        order = int(data.get("order", 99))
    except (TypeError, ValueError) as exc:
        raise TemplateGuardError("order 必须是整数") from exc

    supports = data.get("supports", {})
    if not isinstance(supports, dict):
        supports = {}
    columns = [value for value in supports.get("columns", [1, 2]) if value in (1, 2)]
    divider = [value for value in supports.get("divider", ["line", "block", "none"]) if value in ("line", "block", "none")]
    if not columns:
        raise TemplateGuardError("supports.columns 至少需要声明 1 或 2")
    if not divider:
        raise TemplateGuardError("supports.divider 至少需要声明一种分隔样式")

    return {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
        "color": color,
        "order": max(0, min(order, 999)),
        "serifHeading": bool(data.get("serifHeading", False)),
        "supports": {
            "columns": sorted(set(columns)),
            "photo": bool(supports.get("photo", True)),
            "divider": sorted(set(divider), key=("line", "block", "none").index),
        },
        "variants": _validate_variants(data.get("variants", [])),
        "version": str(data.get("version", "1.0.0")).strip()[:20] or "1.0.0",
        "author": str(data.get("author", "")).strip()[:40],
    }


def _validate_variants(raw: Any) -> list[dict]:
    if raw in (None, ""):
        return []
    if not isinstance(raw, list):
        raise TemplateGuardError("variants 必须是数组")
    if len(raw) > 6:
        raise TemplateGuardError("variants 最多支持 6 组")

    groups: list[dict] = []
    seen: set[str] = set()
    for group in raw:
        if not isinstance(group, dict):
            raise TemplateGuardError("variants 中的每一项必须是对象")
        key = str(group.get("key", "")).strip()
        label = str(group.get("label", "")).strip()
        if not VARIANT_KEY_RE.fullmatch(key):
            raise TemplateGuardError(f"变体 key 不合法：{key or '空'}")
        if key in seen:
            raise TemplateGuardError(f"变体 key 重复：{key}")
        if not label or len(label) > 16:
            raise TemplateGuardError(f"变体 {key} 的名称不能为空且不超过 16 个字")
        options_raw = group.get("options")
        if not isinstance(options_raw, list) or not 2 <= len(options_raw) <= 4:
            raise TemplateGuardError(f"变体 {key} 需要 2~4 个选项")
        options: list[dict] = []
        values: set[str] = set()
        for option in options_raw:
            if not isinstance(option, dict):
                raise TemplateGuardError(f"变体 {key} 的选项必须是对象")
            value = str(option.get("value", "")).strip()
            option_label = str(option.get("label", "")).strip()
            if not VARIANT_VALUE_RE.fullmatch(value) or not option_label or len(option_label) > 12:
                raise TemplateGuardError(f"变体 {key} 的选项不合法")
            if value in values:
                raise TemplateGuardError(f"变体 {key} 的选项值重复：{value}")
            values.add(value)
            options.append({"value": value, "label": option_label})
        default = str(group.get("default", options[0]["value"]))
        if default not in values:
            raise TemplateGuardError(f"变体 {key} 的默认值不在选项中")
        description = str(group.get("description", "")).strip()[:60]
        seen.add(key)
        groups.append(
            {
                "key": key,
                "label": label,
                "description": description,
                "options": options,
                "default": default,
            }
        )
    return groups


def ensure_safe(directory: Path) -> None:
    for filename in ("template.html", "style.css"):
        path = directory / filename
        if not path.is_file():
            raise TemplateGuardError(f"模板缺少 {filename}")
        content = path.read_text(encoding="utf-8")
        check_text_size(content, filename)
        check_markup(content, filename)

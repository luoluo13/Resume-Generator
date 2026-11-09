from __future__ import annotations

import io
import re
from collections import Counter

import pdfplumber

from app.importers.base import Block, ImportParseError, ParseResult, clean_line

BOLD_HINTS = ("bold", "heavy", "black", "semibold", "demi", "simhei", "heiti", "黑体")
SERIF_HINTS = ("song", "serif", "ming", "宋", "仿宋", "明朝")


def _is_bold_font(name: str) -> bool:
    lowered = (name or "").lower()
    return any(hint in lowered for hint in BOLD_HINTS)


def _join_words(words: list[dict]) -> str:
    text = ""
    previous_word: dict | None = None
    for word in words:
        value = clean_line(word.get("text", ""))
        if not value:
            continue
        if not text:
            text = value
            previous_word = word
            continue
        gap = float(word.get("x0", 0)) - float(previous_word.get("x1", 0)) if previous_word else 0
        size = float(word.get("size") or 10)
        previous = text[-1]
        following = value[0]
        if gap > max(2.4, size * 0.22):
            text += " " + value
        elif previous.isascii() and previous.isalnum() and following.isascii() and following.isalnum():
            text += " " + value
        else:
            text += value
        previous_word = word
    return text


def _group_words(words: list[dict], page: int) -> list[dict]:
    if not words:
        return []
    ordered = sorted(words, key=lambda word: (float(word.get("top", 0)), float(word.get("x0", 0))))
    grouped: list[dict] = []
    for word in ordered:
        top = float(word.get("top", 0))
        size = float(word.get("size") or 10)
        target = None
        for line in reversed(grouped[-4:]):
            if abs(line["top"] - top) <= max(2.2, size * 0.32):
                target = line
                break
        if target is None:
            target = {"top": top, "words": [], "page": page}
            grouped.append(target)
        target["words"].append(word)

    lines: list[dict] = []
    for item in grouped:
        item["words"].sort(key=lambda word: float(word.get("x0", 0)))
        text = _join_words(item["words"])
        if not text:
            continue
        sizes = [float(word.get("size") or 0) for word in item["words"] if word.get("size")]
        fonts = [str(word.get("fontname") or "") for word in item["words"]]
        bold_chars = sum(
            len(clean_line(word.get("text", ""))) for word in item["words"] if _is_bold_font(str(word.get("fontname") or ""))
        )
        total_chars = sum(len(clean_line(word.get("text", ""))) for word in item["words"]) or 1
        lines.append(
            {
                "text": text,
                "size": max(sizes) if sizes else 10.0,
                "bold": bold_chars / total_chars >= 0.5,
                "x0": min(float(word.get("x0", 0)) for word in item["words"]),
                "x1": max(float(word.get("x1", 0)) for word in item["words"]),
                "y": item["top"],
                "page": item["page"],
                "fonts": fonts,
                "words": item["words"],
            }
        )
    lines.sort(key=lambda line: (line["page"], line["y"], line["x0"]))
    return lines


def _detect_columns(blocks: list[Block], width: float) -> int:
    if width <= 0 or len(blocks) < 18:
        return 1
    middle = width / 2
    left = [block for block in blocks if block.x1 <= middle - 2]
    right = [block for block in blocks if block.x0 >= middle + 2]
    if len(left) < 8 or len(right) < 8:
        return 1
    if len(left) + len(right) < len(blocks) * 0.6:
        return 1
    left_edge = sorted(block.x1 for block in left)[max(0, int(len(left) * 0.9) - 1)]
    right_edge = sorted(block.x0 for block in right)[max(0, int(len(right) * 0.1))]
    return 2 if right_edge - left_edge > max(10.0, width * 0.03) else 1


def _order_columns(blocks: list[Block], width: float) -> list[Block]:
    middle = width / 2
    ordered: list[Block] = []
    for page in sorted({block.page for block in blocks}):
        page_blocks = [block for block in blocks if block.page == page]
        spanning = [block for block in page_blocks if block.x0 < middle - 2 and block.x1 > middle + 2]
        left = [block for block in page_blocks if block not in spanning and block.x0 < middle]
        right = [block for block in page_blocks if block not in spanning and block.x0 >= middle]
        ordered.extend(sorted(spanning, key=lambda block: block.y))
        ordered.extend(sorted(left, key=lambda block: block.y))
        ordered.extend(sorted(right, key=lambda block: block.y))
    return ordered


def _color_to_hex(color) -> str:
    if color is None:
        return ""
    if isinstance(color, (int, float)):
        value = float(color)
        channels = (value, value, value)
    elif isinstance(color, (list, tuple)):
        if len(color) == 3:
            channels = tuple(float(item) for item in color)
        elif len(color) == 4:
            cyan, magenta, yellow, black = (float(item) for item in color)
            channels = (
                (1 - cyan) * (1 - black),
                (1 - magenta) * (1 - black),
                (1 - yellow) * (1 - black),
            )
        else:
            return ""
    else:
        return ""
    if any(channel > 1.5 for channel in channels):
        channels = tuple(channel / 255 for channel in channels)
    if any(channel < 0 or channel > 1 for channel in channels):
        return ""
    return "#{:02x}{:02x}{:02x}".format(*(round(channel * 255) for channel in channels))


def _is_accent(hex_value: str) -> bool:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_value):
        return False
    red, green, blue = (int(hex_value[index : index + 2], 16) for index in (1, 3, 5))
    high, low = max(red, green, blue), min(red, green, blue)
    if high < 60 or high > 245:
        return False
    return high - low >= 35


def parse_pdf(raw: bytes) -> ParseResult:
    try:
        document = pdfplumber.open(io.BytesIO(raw))
    except Exception as exc:
        raise ImportParseError("无法读取 PDF 文件，请确认文件没有损坏或加密。") from exc

    blocks: list[Block] = []
    warnings: list[str] = []
    colors: Counter[str] = Counter()
    font_chars: Counter[str] = Counter()
    width = 0.0
    pages = 0
    image_count = 0

    try:
        for page_number, page in enumerate(document.pages, start=1):
            pages += 1
            width = width or float(page.width)
            image_count += len(page.images or [])
            try:
                words = page.extract_words(
                    extra_attrs=["size", "fontname", "non_stroking_color"],
                    keep_blank_chars=False,
                )
            except Exception:
                continue
            for line in _group_words(words, page_number):
                if re.fullmatch(r"\d{1,3}", line["text"]) and line["y"] > float(page.height) * 0.88:
                    continue
                blocks.append(
                    Block(
                        text=line["text"],
                        size=line["size"],
                        bold=line["bold"],
                        x0=line["x0"],
                        x1=line["x1"],
                        y=line["y"],
                        page=page_number,
                    )
                )
                for word in line["words"]:
                    font_name = str(word.get("fontname") or "")
                    text_length = len(clean_line(word.get("text", "")))
                    if font_name:
                        font_chars[font_name] += text_length
                    color = _color_to_hex(word.get("non_stroking_color"))
                    if color and _is_accent(color):
                        colors[color] += text_length
    finally:
        document.close()

    if not blocks:
        raise ImportParseError("PDF 中没有可读取的文字，若为扫描件或图片型 PDF 无法导入。")

    columns = _detect_columns(blocks, width)
    if columns == 2:
        blocks = _order_columns(blocks, width)
        warnings.append("检测到双栏排版，已按左栏到右栏的顺序读取，请重点核对模块顺序。")
    if pages > 1:
        warnings.append(f"文档共 {pages} 页，已按页面顺序合并内容。")

    total_chars = sum(font_chars.values()) or 1
    serif_chars = sum(length for name, length in font_chars.items() if any(hint in name.lower() for hint in SERIF_HINTS))
    serif = serif_chars / total_chars >= 0.3

    accent = f"#{colors.most_common(1)[0][0].lstrip('#')}" if colors else ""
    return ParseResult(
        blocks=blocks,
        warnings=warnings,
        pages=pages,
        has_images=image_count > 0,
        columns_hint=columns,
        serif=serif,
        accent=accent,
    )

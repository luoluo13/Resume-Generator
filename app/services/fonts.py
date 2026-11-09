from __future__ import annotations

import os
from pathlib import Path

FONT_CSS = {
    "SourceHanSansSC": '"Source Han Sans SC","Noto Sans SC","Microsoft YaHei","PingFang SC",sans-serif',
    "SourceHanSerifSC": '"Source Han Serif SC","Noto Serif SC","Songti SC","STSong",SimSun,serif',
    "MicrosoftYaHei": '"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif',
}

SERIF_CSS = FONT_CSS["SourceHanSerifSC"]
SANS_CSS = FONT_CSS["MicrosoftYaHei"]

FONT_LABELS = {
    "SourceHanSansSC": "思源黑体",
    "SourceHanSerifSC": "思源宋体",
    "MicrosoftYaHei": "微软雅黑",
}

_FONT_FILES = {
    "SourceHanSansSC": ["SourceHanSansSC-Regular.otf", "NotoSansSC-Regular.otf", "NotoSansCJKsc-Regular.otf"],
    "SourceHanSerifSC": ["SourceHanSerifSC-Regular.otf", "NotoSerifSC-Regular.otf", "NotoSerifCJKsc-Regular.otf"],
    "MicrosoftYaHei": ["msyh.ttc", "msyh.ttf"],
}


def _font_dirs() -> list[Path]:
    candidates = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    return [path for path in candidates if path.exists()]


def _has_font(key: str) -> bool:
    names = {name.lower() for name in _FONT_FILES[key]}
    for folder in _font_dirs():
        try:
            for entry in folder.iterdir():
                if entry.name.lower() in names:
                    return True
        except OSError:
            continue
    return False


def font_state() -> dict:
    available = {key: _has_font(key) for key in FONT_CSS}
    return {
        "ready": any(available.values()),
        "available": available,
        "labels": FONT_LABELS,
        "fallback": FONT_LABELS["MicrosoftYaHei"],
    }


def css_stack(key: str) -> str:
    return FONT_CSS.get(key, FONT_CSS["MicrosoftYaHei"])


def docx_font_details(key: str) -> tuple[str, str]:
    """返回 (正文字体名, 标题衬线字体名)，只使用系统中真实存在的字体，避免 Word 替换提示。"""
    if key == "SourceHanSerifSC":
        body = "Source Han Serif SC" if _has_font("SourceHanSerifSC") else "SimSun"
    elif key == "SourceHanSansSC":
        body = "Source Han Sans SC" if _has_font("SourceHanSansSC") else "Microsoft YaHei"
    else:
        body = "Microsoft YaHei"
    heading = "Source Han Serif SC" if _has_font("SourceHanSerifSC") else "SimSun"
    return body, heading

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SECTION_TYPES = (
    "education",
    "experience",
    "project",
    "skills",
    "awards",
    "certificate",
    "custom",
)

_RICH_TAGS = {"strong", "em", "a", "p", "br"}
_TAG_RE = re.compile(r"<\s*/?\s*([a-zA-Z0-9]+)([^>]*)>")


def sanitize_rich(value: str) -> str:
    """只保留 strong / em / a / p / br，链接仅允许 http(s)。"""
    if not value:
        return ""
    value = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", value)
    value = re.sub(r"(?is)on\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", value)

    def replace(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        raw = match.group(0)
        closing = raw.lstrip().startswith("</")
        if tag not in _RICH_TAGS:
            return ""
        if tag == "a":
            if closing:
                return "</a>"
            href = re.search(r"""href\s*=\s*["']([^"']*)["']""", match.group(2) or "")
            if not href or not re.match(r"^https?://", href.group(1)):
                return ""
            return f'<a href="{href.group(1)}" target="_blank" rel="noopener">'
        if closing:
            return "</p>" if tag == "p" else (f"</{tag}>" if tag in ("strong", "em") else "")
        return f"<{tag}>"

    return _TAG_RE.sub(replace, value).strip()


def plain_text(value: str) -> str:
    text = re.sub(r"(?i)</p\s*>|<br\s*/?>", " ", value or "")
    text = re.sub(r"(?is)<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


class Theme(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template: str = "classic"
    accent: str = Field("#bf4a2e", pattern=r"^#[0-9a-fA-F]{6}$")
    fontFamily: Literal["SourceHanSansSC", "SourceHanSerifSC", "MicrosoftYaHei"] = "SourceHanSansSC"
    fontSize: float = Field(10.5, ge=9, le=12)
    lineHeight: float = Field(1.35, ge=1.0, le=1.6)
    pageMargin: int = Field(18, ge=12, le=25)
    columns: int = Field(1, ge=1, le=2)
    photoPosition: Literal["none", "right", "left"] = "right"
    dividerStyle: Literal["line", "block", "none"] = "line"
    density: Literal["loose", "normal", "compact"] = "normal"
    variants: dict[str, str] = Field(default_factory=dict)

    @field_validator("variants", mode="before")
    @classmethod
    def clean_variants(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {
            str(key)[:24]: str(val)[:24]
            for key, val in value.items()
            if isinstance(key, str) and isinstance(val, (str, int, float))
        }


class Basics(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field("", max_length=30)
    jobIntention: str = Field("", max_length=30)
    phone: str = Field("", max_length=20)
    email: str = Field("", max_length=120)
    city: str = Field("", max_length=20)
    available: str = Field("", max_length=20)
    yearsOfExperience: str = Field("", max_length=20)
    gender: str = Field("", max_length=10)
    birth: str = Field("", max_length=20)
    political: str = Field("", max_length=20)
    photo: str = ""

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value: str) -> str:
        if value and not re.fullmatch(r"[0-9+\-\s()]{6,20}", value):
            raise ValueError("电话格式不正确")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("邮箱格式不正确")
        return value


class Item(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    subtitle: str = ""
    name: str = ""
    school: str = ""
    degree: str = ""
    major: str = ""
    company: str = ""
    role: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    current: bool = False
    gpa: str = ""
    courses: str = ""
    tech: list[str] = Field(default_factory=list)
    link: str = ""
    group: str = ""
    tags: list[str] = Field(default_factory=list)
    issuer: str = ""
    date: str = ""
    highlights: list[str] = Field(default_factory=list)

    @field_validator("highlights", mode="before")
    @classmethod
    def clean_highlights(cls, value: Any) -> list[str]:
        if not value:
            return []
        cleaned = [sanitize_rich(str(entry)) for entry in value]
        return [entry for entry in cleaned if plain_text(entry)]


class Section(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: Literal["education", "experience", "project", "skills", "awards", "certificate", "custom"]
    title: str = Field(..., max_length=20)
    visible: bool = True
    items: list[Item] = Field(default_factory=list)


class Resume(BaseModel):
    model_config = ConfigDict(extra="allow")

    schemaVersion: int = 1
    id: str = "default"
    meta: dict[str, str] = Field(default_factory=dict)
    basics: Basics = Field(default_factory=Basics)
    sections: list[Section] = Field(default_factory=list)
    theme: Theme = Field(default_factory=Theme)

    @field_validator("sections")
    @classmethod
    def check_sections(cls, value: list[Section]) -> list[Section]:
        if not value:
            raise ValueError("至少需要一个模块")
        return value

    @field_validator("meta", mode="before")
    @classmethod
    def clean_meta(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): str(val) for key, val in value.items()}

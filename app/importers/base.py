from __future__ import annotations

import re
from dataclasses import dataclass, field


class ImportParseError(Exception):
    """导入文件无法解析或没有可用内容。"""


@dataclass
class Block:
    """解析后的最小文本块，保留字号、粗细与位置线索。"""

    text: str
    size: float = 0.0
    bold: bool = False
    x0: float = 0.0
    x1: float = 0.0
    y: float = 0.0
    page: int = 1
    table: bool = False

    def stripped(self) -> str:
        return clean_line(self.text)


@dataclass
class ParseResult:
    blocks: list[Block] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pages: int = 1
    has_images: bool = False
    columns_hint: int = 1
    serif: bool = False
    accent: str = ""


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[\s\-]?)?1[3-9]\d{9}(?!\d)")
URL_RE = re.compile(r"https?://[^\s，。；;）)]+")
DATE_TOKEN = r"(?:19|20)\d{2}(?:\s*[./\-年]\s*(?:1[0-2]|0?[1-9])\s*月?)?"
DATE_RANGE_RE = re.compile(
    rf"({DATE_TOKEN})\s*(?:-|–|—|~|～|至|到)\s*"
    rf"({DATE_TOKEN}|至今|现在|今|present|Present|PRESENT|NOW|now)"
)
SINGLE_DATE_RE = re.compile(DATE_TOKEN)
BULLET_RE = re.compile(
    r"^[\s\u3000]*(?:[•·●○▪▫◆◇■□▸▹►▶➢➤*※\-–—]+|[0-9]{1,2}[.、)）]|[（(][0-9一二三四五六七八九十]+[)）])\s*"
)
LABEL_SPLIT_RE = re.compile(r"[|｜·•/／]")
TAG_SPLIT_RE = re.compile(r"[、,，;；/／|｜·]+")
CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b-\u200f\u2028\u2029]")

SECTION_TYPES = ("education", "experience", "project", "skills", "awards", "certificate", "custom")

SECTION_TITLES = {
    "education": "教育背景",
    "experience": "工作经历",
    "project": "项目经历",
    "skills": "专业技能",
    "awards": "荣誉奖项",
    "certificate": "证书资质",
    "custom": "其他信息",
}

HEADING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "education": ("教育背景", "教育经历", "学习经历", "学历背景", "education", "educational"),
    "experience": (
        "工作经历",
        "工作经验",
        "职业经历",
        "实习经历",
        "实习经验",
        "工作履历",
        "workexperience",
        "experience",
        "employment",
    ),
    "project": ("项目经历", "项目经验", "项目实践", "项目作品", "projects", "project"),
    "skills": ("专业技能", "技能特长", "个人技能", "技能清单", "技术栈", "技能", "skills", "skill"),
    "awards": ("荣誉奖项", "获奖情况", "获奖经历", "荣誉奖励", "奖学金", "荣誉", "honors", "awards", "award"),
    "certificate": ("证书资质", "资格证书", "证书", "资质", "certificates", "certificate"),
    "custom": (
        "自我评价",
        "个人评价",
        "个人简介",
        "自我介绍",
        "个人总结",
        "求职意向",
        "求职目标",
        "兴趣爱好",
        "校园经历",
        "社会活动",
        "社会实践",
        "语言能力",
        "附加信息",
        "summary",
        "profile",
        "about",
        "objective",
        "interests",
        "languages",
    ),
}

BASICS_LABELS = (
    "求职意向",
    "意向岗位",
    "目标岗位",
    "应聘职位",
    "期望职位",
    "期望城市",
    "意向城市",
    "现居",
    "居住地",
    "所在地",
    "地址",
    "到岗时间",
    "工作经验",
)


def clean_line(text: str) -> str:
    if not text:
        return ""
    text = CONTROL_RE.sub("", str(text)).replace("\u00a0", " ").replace("\u3000", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def normalize_key(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "", text).lower()


def match_heading(text: str) -> str | None:
    key = normalize_key(text)
    if not key:
        return None
    for section_type, words in HEADING_KEYWORDS.items():
        for word in words:
            target = normalize_key(word)
            if not target:
                continue
            if key == target:
                return section_type
            if key.startswith(target) and len(key) <= len(target) + 4:
                return section_type
            if len(target) >= 4 and target in key and len(key) <= len(target) + 4:
                return section_type
    return None


def match_heading_block(block: Block, body_size: float) -> tuple[str, str] | None:
    text = block.stripped()
    if not text or len(text) > 26:
        return None
    if EMAIL_RE.search(text) or PHONE_RE.search(text) or URL_RE.search(text):
        return None
    if DATE_RANGE_RE.search(text) or SINGLE_DATE_RE.search(text):
        return None
    section_type = match_heading(text)
    if section_type:
        title = SECTION_TITLES[section_type] if re.fullmatch(r"[A-Za-z &/\-·]{2,26}", text) else text
        return section_type, title[:20]
    if block.bold:
        if block.size and body_size and block.size >= body_size + 0.8 and len(text) <= 18:
            if not re.search(r"\d", text) and not re.search(r"[。；;，,！？!?]$", text):
                return "custom", text[:20]
        if re.fullmatch(r"[A-Z][A-Z &/\-·]{1,25}", text):
            return "custom", text[:20]
    return None


def is_bullet(text: str) -> bool:
    return bool(BULLET_RE.match(text))


def strip_bullet(text: str) -> str:
    return BULLET_RE.sub("", text, count=1).strip()


def is_contact_line(text: str) -> bool:
    if re.match(r"^(姓名|名字)\s*[:：]", text):
        return False
    has_token = bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or URL_RE.search(text))
    has_label = bool(re.match(r"^(电话|手机|邮箱|邮件|微信|wechat|qq|地址|现居|所在地)\s*[:：]", text, re.I))
    if not has_token and not has_label:
        return False
    value = EMAIL_RE.sub("", text)
    value = PHONE_RE.sub("", value)
    value = URL_RE.sub("", value)
    value = re.sub(r"[0-9+\-\s()（）|｜·•,，/\\\-–—:：]+", "", value)
    value = re.sub(r"(电话|手机|邮箱|邮件|e-?mail|微信|wechat|qq|地址|现居|所在地)", "", value, flags=re.I)
    return len(value) <= 4


def is_basics_line(text: str) -> bool:
    if match_heading(text):
        return False
    return any(label in text for label in BASICS_LABELS)


def find_period(text: str) -> tuple[str, str, bool] | None:
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None
    start = match.group(1).strip()
    raw_end = match.group(2).strip()
    current = raw_end.lower() in ("至今", "现在", "今", "present", "now")
    return start, ("" if current else raw_end), current


def remove_period(text: str) -> str:
    value = DATE_RANGE_RE.sub(" ", text)
    return re.sub(r"\s{2,}", " ", value).strip(" |｜·-–—:：")


def split_tags(text: str) -> list[str]:
    return [item.strip() for item in TAG_SPLIT_RE.split(text or "") if item.strip()]


def _label_value(lines: list[str], labels: tuple[str, ...]) -> str:
    for index, line in enumerate(lines):
        for label in labels:
            position = line.find(label)
            if position < 0:
                continue
            rest = re.sub(r"^[\s:：|｜·•\-–—]+", "", line[position + len(label) :])
            rest = LABEL_SPLIT_RE.split(rest)[0].strip()
            if rest:
                return rest[:30]
            for follow in lines[index + 1 : index + 3]:
                follow = follow.strip()
                if follow:
                    return follow[:30]
    return ""


def extract_basics(blocks: list[Block]) -> dict[str, str]:
    texts = [block.stripped() for block in blocks if block.stripped()]
    if not texts:
        return {}
    joined = "\n".join(texts)
    front = texts[:14]

    phone_match = PHONE_RE.search(joined)
    email_match = EMAIL_RE.search(joined)
    years = ""
    years_match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:工作)?经验", joined)
    if years_match:
        years = f"{years_match.group(1)}年"
    else:
        years = _label_value(front, ("工作经验",))

    available = _label_value(front, ("到岗时间",))
    if not available:
        available_match = re.search(r"(随时到岗|一个月内到岗|一周内到岗|面议)", joined)
        available = available_match.group(1) if available_match else ""

    return {
        "jobIntention": _label_value(front, ("求职意向", "意向岗位", "目标岗位", "应聘职位", "期望职位")),
        "phone": phone_match.group(0).strip() if phone_match else "",
        "email": email_match.group(0).strip() if email_match else "",
        "city": _label_value(front, ("现居", "居住地", "所在地", "期望城市", "意向城市", "地址")),
        "available": available,
        "yearsOfExperience": years,
    }


def detect_name(blocks: list[Block], body_size: float) -> str:
    candidates = [block for block in blocks[:10] if block.stripped()]
    for block in candidates:
        text = block.stripped()
        match = re.match(r"^(?:姓名|名字)\s*[:：]\s*(.{1,20})$", text)
        if match:
            return match.group(1).strip()[:20]

    for block in candidates[:6]:
        text = block.stripped()
        if not text or len(text) > 30:
            continue
        if EMAIL_RE.search(text) or PHONE_RE.search(text):
            first = re.split(r"\s{2,}|\s+|\|｜", text)[0].strip()
            if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", first) and first not in BASICS_LABELS:
                return first
            continue
        if URL_RE.search(text):
            continue
        if is_contact_line(text) or is_basics_line(text):
            continue
        if match_heading(text):
            continue
        if re.search(r"\d", text) or re.search(r"[。；;，,！？!?]", text):
            continue
        if block.size and body_size and block.size >= body_size + 2:
            return text[:20]

    for block in candidates[:3]:
        text = block.stripped()
        parts = re.split(r"\s{2,}|[|｜·•]", text)
        first = parts[0].strip() if parts else ""
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", first):
            return first
    return ""

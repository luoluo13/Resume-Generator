from __future__ import annotations

import asyncio
import copy
import json
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from app.config import EXPORTS_DIR
from app.deps import exporter, registry, store
from app.models import SECTION_TYPES, Resume
from app.services.exporter import ExportError, sanitize_filename
from app.services.settings import DEEPSEEK_BASE, load_ai
from app.services.store import StoreError

MAX_TOOL_ROUNDS = 8
PENDING_TTL = 30 * 60

SECTION_TITLES = {
    "education": "教育背景",
    "experience": "工作经历",
    "project": "项目经历",
    "skills": "专业技能",
    "awards": "荣誉奖项",
    "certificate": "证书资质",
    "custom": "自定义模块",
}

BASIC_RULES = {
    "name": 30,
    "jobIntention": 30,
    "phone": 20,
    "email": 120,
    "city": 20,
    "available": 20,
    "yearsOfExperience": 20,
    "gender": 10,
    "birth": 20,
    "political": 20,
}

ITEM_TEXT_FIELDS = (
    "title",
    "subtitle",
    "name",
    "school",
    "degree",
    "major",
    "company",
    "role",
    "location",
    "start",
    "end",
    "gpa",
    "courses",
    "link",
    "group",
    "issuer",
    "date",
)

THEME_FIELDS = (
    "accent",
    "fontFamily",
    "fontSize",
    "lineHeight",
    "pageMargin",
    "columns",
    "photoPosition",
    "dividerStyle",
    "density",
)


class ChatError(Exception):
    pass


class ToolError(Exception):
    pass


_pending_lock = threading.Lock()
_pending: dict[str, dict[str, Any]] = {}


def _prune_pending() -> None:
    now = time.time()
    with _pending_lock:
        for key in [key for key, item in _pending.items() if now - item["created"] > PENDING_TTL]:
            _pending.pop(key, None)


def _endpoint(base_url: str, path: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ChatError("尚未配置接口地址")
    if base.endswith(path):
        return base
    return f"{base}{path}"


def _headers(config: dict[str, Any]) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {str(config.get('apiKey') or '').strip()}",
    }


def _error_message(body: bytes, status: int) -> str:
    text = body.decode("utf-8", "ignore").strip()
    try:
        data = json.loads(text)
        error = data.get("error")
        message = error.get("message") if isinstance(error, dict) else data.get("message")
        detail = ""
        if isinstance(error, dict):
            metadata = error.get("metadata")
            if isinstance(metadata, dict):
                raw = str(metadata.get("raw") or "").strip()
                provider = str(metadata.get("provider_name") or "").strip()
                if raw:
                    detail = raw
                    if "region" in raw.lower():
                        detail = f"{raw}（当前网络所在地区不可用，请更换模型或调整网络环境）"
                if provider:
                    detail = f"{detail}（来源：{provider}）" if detail else f"来源：{provider}"
        if message:
            suffix = f"；{detail}" if detail and detail not in str(message) else ""
            return f"接口返回 {status}：{str(message)[:200]}{suffix[:200]}"
        if detail:
            return f"接口返回 {status}：{detail[:200]}"
    except json.JSONDecodeError:
        pass
    if status == 401:
        return "API Key 无效或已过期，请重新填写"
    if status == 402:
        return "账户余额不足，请前往供应商控制台充值"
    return f"接口返回 {status}：{text[:200] or '无响应内容'}"


def _request_json(url: str, headers: dict[str, str], payload: dict[str, Any] | None, timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        raise ChatError(_error_message(exc.read(), exc.code)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ChatError(f"无法连接模型服务：{getattr(exc, 'reason', exc)}") from exc
    except json.JSONDecodeError as exc:
        raise ChatError("模型服务返回的内容不是合法 JSON") from exc


def test_connection(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("provider") == "deepseek":
        base = DEEPSEEK_BASE
    else:
        base = str(config.get("baseUrl") or "").strip()
        if not base.startswith(("http://", "https://")):
            return {"ok": False, "message": "请填写以 http:// 或 https:// 开头的接口地址"}
        if not str(config.get("model") or "").strip():
            return {"ok": False, "message": "请填写模型名称"}
    model = str(config.get("model") or "").strip()
    try:
        _request_json(_endpoint(base, "/models"), _headers(config), None, 20)
        _request_json(
            _endpoint(base, "/chat/completions"),
            _headers(config),
            {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
            },
            60,
        )
    except ChatError as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": "连接成功，可以开始对话"}


def _completion(config: dict[str, Any], messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    model = str(config.get("model") or "").strip()
    if not model:
        raise ChatError("尚未选择模型")
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 2400,
    }
    result = _request_json(
        _endpoint(str(config.get("baseUrl") or ""), "/chat/completions"),
        _headers(config),
        payload,
        120,
    )
    try:
        message = result["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ChatError("模型返回结构异常，未找到回复内容") from exc
    if not isinstance(message, dict):
        raise ChatError("模型返回结构异常，未找到回复内容")
    return message


def _item_schema() -> dict[str, Any]:
    text = lambda desc: {"type": "string", "description": desc}
    return {
        "type": "object",
        "properties": {
            "title": text("条目标题，自定义模块使用"),
            "subtitle": text("补充说明"),
            "name": text("项目名称、奖项名称或证书名称"),
            "school": text("学校名称"),
            "degree": text("学历，如 本科 / 硕士"),
            "major": text("专业"),
            "company": text("公司名称"),
            "role": text("职位或角色"),
            "location": text("地点"),
            "start": text("开始时间，如 2021.03"),
            "end": text("结束时间，如 2023.06"),
            "current": {"type": "boolean", "description": "是否至今仍在进行"},
            "gpa": text("绩点或成绩"),
            "courses": text("主修课程"),
            "tech": {"type": "array", "items": {"type": "string"}, "description": "技术栈标签"},
            "link": text("相关链接"),
            "group": text("技能分组名称"),
            "tags": {"type": "array", "items": {"type": "string"}, "description": "技能或标签列表"},
            "issuer": text("颁发机构"),
            "date": text("获得时间"),
            "highlights": {
                "type": "array",
                "items": {"type": "string"},
                "description": "经历要点，每项一句话，可含 <strong> 强调",
            },
        },
        "additionalProperties": False,
    }


def _tools() -> list[dict[str, Any]]:
    item_schema = _item_schema()
    item_update = copy.deepcopy(item_schema)
    item_update.pop("additionalProperties", None)
    item_update["required"] = ["section_id", "item_index"]
    item_update["properties"] = {
        "section_id": {"type": "string", "description": "目标模块 id"},
        "item_index": {"type": "integer", "minimum": 0, "description": "条目序号，从 0 开始"},
        **item_schema["properties"],
    }
    add_item = copy.deepcopy(item_schema)
    add_item.pop("additionalProperties", None)
    add_item["required"] = ["section_id"]
    add_item["properties"] = {
        "section_id": {"type": "string", "description": "目标模块 id"},
        **item_schema["properties"],
    }

    return [
        {
            "type": "function",
            "function": {
                "name": "get_resume",
                "description": "读取当前操作简历的完整数据，包含基本信息、模块、条目和主题设置。修改前应先调用。",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_resumes",
                "description": "列出本机保存的所有简历，包含简历 id、名称、候选人姓名和更新时间。",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_resume",
                "description": "只读查看另一份简历的完整内容，用于对比或参考。不会修改任何数据。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resume_id": {"type": "string", "description": "要查看的简历 id，可从 list_resumes 获取"}
                    },
                    "required": ["resume_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_basics",
                "description": "修改基本信息。只传需要修改的字段，传空字符串表示清空该字段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        key: {"type": "string", "description": key}
                        for key in BASIC_RULES
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_section",
                "description": "新增一个简历模块，返回新模块的 section_id。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": list(SECTION_TYPES)},
                        "title": {"type": "string", "maxLength": 20, "description": "模块标题，留空使用默认标题"},
                    },
                    "required": ["type"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_section",
                "description": "修改模块的标题、类型或显示状态。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "title": {"type": "string", "maxLength": 20},
                        "type": {"type": "string", "enum": list(SECTION_TYPES)},
                        "visible": {"type": "boolean"},
                    },
                    "required": ["section_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_section",
                "description": "删除整个模块及其全部条目。属于危险操作，调用后需要用户确认。",
                "parameters": {
                    "type": "object",
                    "properties": {"section_id": {"type": "string"}},
                    "required": ["section_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reorder_sections",
                "description": "按给定顺序重排全部模块，order 必须包含所有模块 id。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {"type": "array", "items": {"type": "string"}, "description": "模块 id 的新顺序"}
                    },
                    "required": ["order"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_item",
                "description": "在指定模块中新增一条条目。",
                "parameters": add_item,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_item",
                "description": "修改指定模块中某条条目的字段，item_index 从 0 开始。",
                "parameters": item_update,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_item",
                "description": "删除指定模块中的一条条目。属于危险操作，调用后需要用户确认。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "item_index": {"type": "integer", "minimum": 0},
                    },
                    "required": ["section_id", "item_index"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "move_item",
                "description": "调整同一模块内条目的顺序。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "from_index": {"type": "integer", "minimum": 0},
                        "to_index": {"type": "integer", "minimum": 0},
                    },
                    "required": ["section_id", "from_index", "to_index"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_templates",
                "description": "列出所有可用模板，包含 id、名称、说明和排版能力。",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_template",
                "description": "切换简历模板，只改变排版与配色，不修改内容。",
                "parameters": {
                    "type": "object",
                    "properties": {"template_id": {"type": "string"}},
                    "required": ["template_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_theme",
                "description": "修改主题与排版参数。只传需要修改的字段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "accent": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                        "fontFamily": {"type": "string", "enum": ["SourceHanSansSC", "SourceHanSerifSC", "MicrosoftYaHei"]},
                        "fontSize": {"type": "number", "minimum": 9, "maximum": 12},
                        "lineHeight": {"type": "number", "minimum": 1, "maximum": 1.6},
                        "pageMargin": {"type": "integer", "minimum": 12, "maximum": 25},
                        "columns": {"type": "integer", "enum": [1, 2]},
                        "photoPosition": {"type": "string", "enum": ["none", "right", "left"]},
                        "dividerStyle": {"type": "string", "enum": ["line", "block", "none"]},
                        "density": {"type": "string", "enum": ["loose", "normal", "compact"]},
                        "variants": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_resume",
                "description": "把当前简历导出为 PDF、PNG 或 DOCX 文件，保存到项目的 exports 目录。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["pdf", "png", "docx"]},
                        "file_name": {"type": "string", "description": "文件名，可省略"},
                    },
                    "required": ["format"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_json",
                "description": "把当前简历完整数据导出为 JSON 备份文件，保存到 exports 目录。",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
    ]


def _summary(data: dict[str, Any]) -> str:
    basics = data.get("basics", {})
    theme = data.get("theme", {})
    lines = [
        f"姓名：{basics.get('name') or '未填写'}；求职意向：{basics.get('jobIntention') or '未填写'}",
        "模块：",
    ]
    for index, section in enumerate(data.get("sections", [])):
        lines.append(
            f"- [{index}] {section.get('title')}（id={section.get('id')}，type={section.get('type')}，"
            f"{'显示' if section.get('visible', True) else '隐藏'}，{len(section.get('items', []))} 条）"
        )
    lines.append(
        f"当前模板：{theme.get('template')}；强调色：{theme.get('accent')}；栏数：{theme.get('columns')}；"
        f"字号：{theme.get('fontSize')}pt"
    )
    return "\n".join(lines)


def _system_prompt(data: dict[str, Any], resume_name: str, resume_id: str) -> str:
    return f"""你是「简历工坊」内置的 AI 简历助手，通过工具直接操作本机简历数据。

能力范围：修改基本信息、增删改模块、增删改排序条目、切换模板、调整主题排版、导出 PDF / PNG / DOCX / JSON。

当前操作简历：{resume_name}（id={resume_id}）。所有修改只会作用于这份简历。
使用 list_resumes 可以查看本机全部简历，使用 read_resume 可以只读查看其他简历，用于对比或参考，但不能修改它们。如果用户要求修改其他简历，提醒用户先在会话上方切换操作简历。

规则：
1. 用户要求修改简历时，必须调用工具真正执行，不能只描述“将会修改”。
2. 修改前先调用 get_resume 查看完整内容；不确定 section_id 或 item_index 时先读取。
3. 禁止编造经历、学历、数据或时间；信息不足时先向用户追问。
4. 删除模块、删除条目是危险操作：调用工具后会返回待确认状态，此时要告诉用户在下方确认卡片中确认，不能声称已经删除。
5. 一个需求可以连续调用多个工具，完成后用简体中文简要说明改了什么。
6. 全部回复必须是纯文本，禁止使用 Markdown：不要使用 # 标题、** 加粗、反引号代码、表格、代码块或 - 列表符号。需要列举时使用中文序号（1. 2. 3.）或自然语言句子，用换行分段。
7. 不要输出 HTML，不要粘贴大段 JSON，不要编造不存在的工具或字段。
8. 用户只是咨询建议时，可以直接回答，不必调用工具。

当前简历概况：
{_summary(data)}
"""


_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def plain_reply(value: str) -> str:
    """把模型回复中常见的 Markdown 标记清理为纯文本。"""
    text = (value or "").replace("\r\n", "\n")
    text = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s{0,3}>\s?", "", text)
    text = _MD_LINK.sub(lambda match: f"{match.group(1)}（{match.group(2)}）", text)
    text = re.sub(r"(?m)^\s{0,3}[-*+]\s+", "· ", text)
    text = re.sub(r"(?m)^\s*\|?[-:| ]{3,}\|?\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_section(data: dict[str, Any], section_id: str) -> dict[str, Any]:
    for section in data.get("sections", []):
        if section.get("id") == section_id:
            return section
    raise ToolError("找不到该模块，请先调用 get_resume 获取最新的 section_id")


def _find_item(section: dict[str, Any], index: Any) -> tuple[int, dict[str, Any]]:
    items = section.setdefault("items", [])
    try:
        position = int(index)
    except (TypeError, ValueError) as exc:
        raise ToolError("item_index 必须是整数") from exc
    if position < 0 or position >= len(items):
        raise ToolError(f"条目序号超出范围，当前模块共有 {len(items)} 条")
    return position, items[position]


def _apply(state: dict[str, Any], mutate) -> None:
    before = copy.deepcopy(state["data"])
    try:
        mutate(state["data"])
        state["data"] = Resume.model_validate(state["data"]).model_dump(mode="json")
    except ToolError:
        state["data"] = before
        raise
    except Exception as exc:  # pydantic 校验失败等
        state["data"] = before
        raise ToolError(f"修改未生效：{exc}") from exc
    state["changed"] = True


def _item_values(args: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in ITEM_TEXT_FIELDS:
        value = args.get(field)
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int, float)):
            values[field] = str(value).strip()
    if isinstance(args.get("current"), bool):
        values["current"] = args["current"]
    for field, limit in (("tech", 40), ("tags", 40), ("highlights", 80)):
        raw = args.get(field)
        if isinstance(raw, list):
            values[field] = [str(entry).strip()[:300] for entry in raw if str(entry).strip()][:limit]
    return values


def _action(state: dict[str, Any], tool: str, label: str, detail: str = "") -> None:
    state["actions"].append({"tool": tool, "label": label, "detail": detail})


def _pending_confirmation(
    state: dict[str, Any],
    tool: str,
    args: dict[str, Any],
    title: str,
    summary: str,
) -> dict[str, Any]:
    _prune_pending()
    confirmation_id = uuid.uuid4().hex[:12]
    record = {
        "id": confirmation_id,
        "tool": tool,
        "args": args,
        "title": title,
        "summary": summary,
        "resume_id": state["resume_id"],
        "created": time.time(),
    }
    with _pending_lock:
        _pending[confirmation_id] = record
    state["pending"].append({"id": confirmation_id, "tool": tool, "title": title, "summary": summary})
    return {
        "status": "pending_confirmation",
        "confirmationId": confirmation_id,
        "message": f"{summary}。需要用户在确认卡片中点击确认后才会执行。",
    }


def _template_manifest(template_id: str) -> dict[str, Any]:
    for manifest in registry.list():
        if manifest.get("id") == template_id:
            return manifest
    raise ToolError("找不到该模板，请先调用 list_templates")


def _apply_template(data: dict[str, Any], template_id: str) -> dict[str, Any]:
    manifest = _template_manifest(template_id)
    theme = data.setdefault("theme", {})
    theme["template"] = template_id
    theme["variants"] = {}
    supports = manifest.get("supports") or {}
    columns = supports.get("columns") or [1, 2]
    if theme.get("columns") not in columns:
        theme["columns"] = columns[0]
    if not supports.get("photo", True):
        theme["photoPosition"] = "none"
    dividers = supports.get("divider") or ["line", "block", "none"]
    if theme.get("dividerStyle") not in dividers:
        theme["dividerStyle"] = dividers[0]
    return manifest


def _execute_tool_sync(state: dict[str, Any], name: str, args: dict[str, Any]) -> dict[str, Any]:
    data = state["data"]

    if name == "get_resume":
        return {"resume": data, "resumeId": state["resume_id"]}

    if name == "list_resumes":
        return {"resumes": store.list_resumes(), "operatingResumeId": state["resume_id"]}

    if name == "read_resume":
        target_id = str(args.get("resume_id") or "").strip()
        if not target_id:
            raise ToolError("缺少 resume_id")
        if target_id == state["resume_id"]:
            return {"resume": data, "resumeId": target_id, "readOnly": False}
        try:
            other = store.load(target_id)
        except StoreError as exc:
            raise ToolError("找不到该简历，请先调用 list_resumes") from exc
        item = next((entry for entry in store.list_resumes() if entry["id"] == target_id), None)
        return {
            "resume": other,
            "resumeId": target_id,
            "resumeName": item["name"] if item else "",
            "readOnly": True,
        }

    if name == "update_basics":
        changes = {}
        for key, limit in BASIC_RULES.items():
            value = args.get(key)
            if isinstance(value, (str, int, float)):
                changes[key] = str(value).strip()[:limit]
        if not changes:
            raise ToolError("没有需要修改的基本信息字段")
        _apply(state, lambda current: current.setdefault("basics", {}).update(changes))
        _action(state, name, "更新基本信息", "、".join(changes.keys()))
        return {"ok": True, "updated": changes}

    if name == "add_section":
        section_type = str(args.get("type") or "")
        if section_type not in SECTION_TYPES:
            raise ToolError("模块类型不合法")
        title = str(args.get("title") or "").strip()[:20] or SECTION_TITLES[section_type]
        section_id = f"sec_{uuid.uuid4().hex[:8]}"
        _apply(state, lambda current: current.setdefault("sections", []).append(
            {"id": section_id, "type": section_type, "title": title, "visible": True, "items": []}
        ))
        _action(state, name, f"新增模块「{title}」")
        return {"ok": True, "sectionId": section_id, "title": title}

    if name == "update_section":
        section = _find_section(data, str(args.get("section_id") or ""))
        changes = {}
        if isinstance(args.get("title"), str) and args["title"].strip():
            changes["title"] = args["title"].strip()[:20]
        if args.get("type") in SECTION_TYPES:
            changes["type"] = args["type"]
        if isinstance(args.get("visible"), bool):
            changes["visible"] = args["visible"]
        if not changes:
            raise ToolError("没有需要修改的模块字段")
        _apply(state, lambda current: _find_section(current, section["id"]).update(changes))
        _action(state, name, f"更新模块「{section['title']}」", "、".join(changes.keys()))
        return {"ok": True, "sectionId": section["id"], "updated": changes}

    if name == "delete_section":
        section = _find_section(data, str(args.get("section_id") or ""))
        return _pending_confirmation(
            state,
            name,
            {"section_id": section["id"]},
            "删除模块",
            f"删除模块「{section['title']}」及其 {len(section.get('items', []))} 条内容",
        )

    if name == "reorder_sections":
        order = args.get("order")
        if not isinstance(order, list):
            raise ToolError("order 必须是模块 id 数组")
        sections = data.get("sections", [])
        ids = [str(entry) for entry in order]
        if sorted(ids) != sorted(section.get("id") for section in sections):
            raise ToolError("order 必须包含全部且仅包含现有的模块 id")

        def reorder(current: dict[str, Any]) -> None:
            mapping = {section["id"]: section for section in current.get("sections", [])}
            current["sections"] = [mapping[section_id] for section_id in ids]

        _apply(state, reorder)
        _action(state, name, "调整模块顺序")
        return {"ok": True, "order": ids}

    if name == "add_item":
        section = _find_section(data, str(args.get("section_id") or ""))
        values = _item_values(args)
        if not values:
            raise ToolError("没有提供条目内容")
        new_index = len(section.get("items", []))
        _apply(state, lambda current: _find_section(current, section["id"]).setdefault("items", []).append(values))
        _action(state, name, f"在「{section['title']}」新增条目", values.get("name") or values.get("company") or values.get("school") or "")
        return {"ok": True, "sectionId": section["id"], "itemIndex": new_index}

    if name == "update_item":
        section = _find_section(data, str(args.get("section_id") or ""))
        position, item = _find_item(section, args.get("item_index"))
        values = _item_values(args)
        if not values:
            raise ToolError("没有提供需要修改的条目字段")

        def update(current: dict[str, Any]) -> None:
            target = _find_section(current, section["id"])["items"][position]
            target.update(values)

        _apply(state, update)
        label = values.get("name") or values.get("company") or values.get("school") or f"第 {position + 1} 条"
        _action(state, name, f"更新「{section['title']}」中的 {label}", "、".join(values.keys()))
        return {"ok": True, "sectionId": section["id"], "itemIndex": position}

    if name == "delete_item":
        section = _find_section(data, str(args.get("section_id") or ""))
        position, item = _find_item(section, args.get("item_index"))
        label = item.get("name") or item.get("company") or item.get("school") or f"第 {position + 1} 条"
        return _pending_confirmation(
            state,
            name,
            {"section_id": section["id"], "item_index": position},
            "删除条目",
            f"删除「{section['title']}」中的「{label}」",
        )

    if name == "move_item":
        section = _find_section(data, str(args.get("section_id") or ""))
        position, _ = _find_item(section, args.get("from_index"))
        total = len(section.get("items", []))
        try:
            target = int(args.get("to_index"))
        except (TypeError, ValueError) as exc:
            raise ToolError("to_index 必须是整数") from exc
        if target < 0 or target >= total:
            raise ToolError(f"目标序号超出范围，当前模块共有 {total} 条")

        def move(current: dict[str, Any]) -> None:
            items = _find_section(current, section["id"])["items"]
            items.insert(target, items.pop(position))

        _apply(state, move)
        _action(state, name, f"调整「{section['title']}」条目顺序", f"{position + 1} → {target + 1}")
        return {"ok": True, "sectionId": section["id"], "from": position, "to": target}

    if name == "list_templates":
        return {
            "templates": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "tags": item.get("tags", []),
                    "supports": item.get("supports", {}),
                    "variants": [
                        {
                            "key": variant.get("key"),
                            "label": variant.get("label"),
                            "options": [
                                {"value": option.get("value"), "label": option.get("label")}
                                for option in variant.get("options", [])
                            ],
                        }
                        for variant in item.get("variants", [])
                    ],
                }
                for item in registry.list()
            ]
        }

    if name == "set_template":
        template_id = str(args.get("template_id") or "")
        manifest = _template_manifest(template_id)
        _apply(state, lambda current: _apply_template(current, template_id))
        _action(state, name, f"切换模板为「{manifest.get('name')}」")
        return {"ok": True, "templateId": template_id}

    if name == "set_theme":
        changes: dict[str, Any] = {}
        for field in THEME_FIELDS:
            if field in args and args[field] is not None:
                changes[field] = args[field]
        variants = args.get("variants")
        if isinstance(variants, dict):
            changes["variants"] = {
                str(key)[:24]: str(value)[:24] for key, value in variants.items() if isinstance(value, (str, int, float))
            }
        if not changes:
            raise ToolError("没有需要修改的主题字段")
        _apply(state, lambda current: current.setdefault("theme", {}).update(changes))
        _action(state, name, "调整主题排版", "、".join(changes.keys()))
        return {"ok": True, "updated": changes}

    raise ToolError(f"未知工具：{name}")


async def _execute_tool(state: dict[str, Any], name: str, args: dict[str, Any], base_url: str) -> dict[str, Any]:
    if name == "export_resume":
        fmt = str(args.get("format") or "")
        if fmt not in ("pdf", "png", "docx"):
            raise ToolError("导出格式只支持 pdf、png、docx")
        if state["changed"]:
            _save(state)
        try:
            result = await exporter.export(
                fmt,
                state["data"],
                state["data"].get("theme", {}),
                base_url,
                str(args.get("file_name") or "").strip() or None,
            )
        except ExportError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"导出失败：{exc}") from exc
        files = "、".join(item["name"] for item in result.get("files", []))
        _action(state, name, f"导出 {fmt.upper()}", files)
        return {"ok": True, "format": fmt, "files": result.get("files", []), "dir": result.get("dir")}

    if name == "export_json":
        if state["changed"]:
            _save(state)
        name_base = sanitize_filename(state["data"].get("basics", {}).get("name") or "简历")
        target = EXPORTS_DIR / f"{name_base}_resume.json"
        index = 2
        while target.exists():
            target = EXPORTS_DIR / f"{name_base}_resume-{index}.json"
            index += 1
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state["data"], ensure_ascii=False, indent=2), encoding="utf-8")
        _action(state, name, "导出 JSON 备份", target.name)
        return {"ok": True, "file": {"name": target.name, "path": str(target)}}

    return _execute_tool_sync(state, name, args)


def _save(state: dict[str, Any]) -> None:
    resume_id = state["resume_id"]
    if not state.get("snapshot"):
        store.snapshot(resume_id)
        state["snapshot"] = True
    stamp = store.save(state["data"], resume_id)
    state["data"].setdefault("meta", {})["updatedAt"] = stamp
    state["changed"] = False


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError("工具参数不是合法 JSON") from exc
    return data if isinstance(data, dict) else {}


def _clean_history(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    messages: list[dict[str, str]] = []
    for entry in raw[-24:]:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:6000]})
    return messages


def _resolve_config() -> dict[str, Any]:
    config = load_ai()
    if not config.get("apiKey"):
        raise ChatError("尚未配置 API Key，请先在 AI 助手中填写")
    return config


async def run_chat(history: Any, message: str, base_url: str, resume_id: str) -> dict[str, Any]:
    text = (message or "").strip()
    if not text:
        raise ChatError("请输入内容")
    config = _resolve_config()
    items = store.list_resumes()
    target = next((item for item in items if item["id"] == resume_id), None)
    if target is None:
        raise ChatError("找不到要操作的简历，请重新选择")

    state: dict[str, Any] = {
        "data": store.load(resume_id),
        "resume_id": resume_id,
        "changed": False,
        "snapshot": False,
        "actions": [],
        "pending": [],
    }
    messages = [{"role": "system", "content": _system_prompt(state["data"], target["name"], resume_id)}]
    messages.extend(_clean_history(history))
    messages.append({"role": "user", "content": text[:6000]})

    tools = _tools()
    reply = ""
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            message_data = await asyncio.to_thread(_completion, config, messages, tools)
            content = message_data.get("content") or ""
            tool_calls = message_data.get("tool_calls") or []
            if not tool_calls:
                reply = str(content).strip()
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                function = call.get("function") if isinstance(call, dict) else None
                name = str((function or {}).get("name") or "")
                try:
                    args = _parse_arguments((function or {}).get("arguments"))
                    result = await _execute_tool(state, name, args, base_url)
                except ToolError as exc:
                    result = {"ok": False, "error": str(exc)}
                except ChatError:
                    raise
                except Exception as exc:
                    result = {"ok": False, "error": f"工具执行失败：{exc}"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": json.dumps(result, ensure_ascii=False)[:12000],
                    }
                )
        else:
            reply = "这次操作步骤较多，请把需求拆成几步再试。"
    finally:
        if state["changed"]:
            _save(state)

    reply = plain_reply(reply)
    if not reply:
        reply = "已完成相关操作。" if state["actions"] or state["pending"] else "我在这里，请告诉我需要怎么调整简历。"

    return {
        "reply": reply,
        "actions": state["actions"],
        "pending": state["pending"],
        "resume": state["data"] if state["actions"] else None,
        "changed": bool(state["actions"]),
        "resumeId": resume_id,
    }


def confirm_action(confirmation_id: str, approve: bool) -> dict[str, Any]:
    _prune_pending()
    with _pending_lock:
        record = _pending.pop(confirmation_id, None)
    if not record:
        raise ChatError("该确认已失效，请重新发起操作")

    summary = record["summary"]
    resume_id = str(record.get("resume_id") or store.active_id())
    if not approve:
        return {"ok": True, "cancelled": True, "message": f"已取消：{summary}", "resume": None, "resumeId": resume_id}

    state: dict[str, Any] = {
        "data": store.load(resume_id),
        "resume_id": resume_id,
        "changed": False,
        "snapshot": False,
        "actions": [],
        "pending": [],
    }
    tool = record["tool"]
    args = record["args"]
    try:
        if tool == "delete_section":
            section = _find_section(state["data"], str(args.get("section_id") or ""))
            if len(state["data"].get("sections", [])) <= 1:
                raise ToolError("至少需要保留一个模块")
            _apply(state, lambda current: current.update(
                {"sections": [item for item in current.get("sections", []) if item.get("id") != section["id"]]}
            ))
        elif tool == "delete_item":
            section = _find_section(state["data"], str(args.get("section_id") or ""))
            position, _ = _find_item(section, args.get("item_index"))
            _apply(state, lambda current: _find_section(current, section["id"])["items"].pop(position))
        else:
            raise ToolError("不支持的确认操作")
    except ToolError as exc:
        raise ChatError(str(exc)) from exc

    if state["changed"]:
        _save(state)
    return {
        "ok": True,
        "cancelled": False,
        "message": f"{summary}：已执行",
        "resume": state["data"],
        "resumeId": resume_id,
    }

from __future__ import annotations

import json
from typing import Any

from app.config import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"

PROVIDERS = ("deepseek", "custom")
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODELS = ("deepseek-chat", "deepseek-reasoner")

DEFAULT_AI: dict[str, Any] = {
    "provider": "deepseek",
    "baseUrl": DEEPSEEK_BASE,
    "model": "deepseek-chat",
    "apiKey": "",
}


class SettingsError(Exception):
    pass


def _read() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    ai = dict(DEFAULT_AI)
    provider = raw.get("provider")
    if provider in PROVIDERS:
        ai["provider"] = provider
    key = raw.get("apiKey")
    if isinstance(key, str):
        ai["apiKey"] = key.strip()
    if ai["provider"] == "deepseek":
        ai["baseUrl"] = DEEPSEEK_BASE
        model = raw.get("model")
        ai["model"] = model if model in DEEPSEEK_MODELS else DEEPSEEK_MODELS[0]
    else:
        ai["baseUrl"] = str(raw.get("baseUrl") or "").strip()
        ai["model"] = str(raw.get("model") or "").strip()
    return ai


def load_ai() -> dict[str, Any]:
    raw = _read().get("ai")
    return _normalize(raw if isinstance(raw, dict) else {})


def save_ai(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_ai()
    provider = patch.get("provider")
    if provider is not None:
        if provider not in PROVIDERS:
            raise SettingsError("不支持的供应商")
        current["provider"] = provider

    if current["provider"] == "custom":
        base_url = patch.get("baseUrl")
        model = patch.get("model")
        if isinstance(base_url, str):
            current["baseUrl"] = base_url.strip()
        if isinstance(model, str):
            current["model"] = model.strip()

    key = patch.get("apiKey")
    if isinstance(key, str) and key.strip():
        current["apiKey"] = key.strip()
    elif patch.get("clearKey"):
        current["apiKey"] = ""

    ai = _normalize(current)
    if ai["provider"] == "custom":
        if not ai["baseUrl"].startswith(("http://", "https://")):
            raise SettingsError("请填写以 http:// 或 https:// 开头的接口地址")
        if not ai["model"]:
            raise SettingsError("请填写自定义供应商的模型名称")

    data = _read()
    data["ai"] = ai
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(SETTINGS_FILE)
    return ai


def public_ai(ai: dict[str, Any]) -> dict[str, Any]:
    key = str(ai.get("apiKey") or "")
    return {
        "provider": ai.get("provider", "deepseek"),
        "baseUrl": str(ai.get("baseUrl") or ""),
        "model": str(ai.get("model") or ""),
        "hasKey": bool(key),
        "keyHint": f"••••{key[-4:]}" if len(key) >= 8 else "",
        "models": list(DEEPSEEK_MODELS),
    }


def merge_ai(patch: dict[str, Any]) -> dict[str, Any]:
    """用请求里的临时值覆盖已保存配置，用于「测试连接」而不落盘。"""
    ai = load_ai()
    provider = patch.get("provider")
    switching = provider in PROVIDERS and provider != ai["provider"]
    if provider in PROVIDERS:
        ai["provider"] = provider
    if ai["provider"] == "deepseek":
        ai["baseUrl"] = DEEPSEEK_BASE
        model = patch.get("model")
        ai["model"] = model if model in DEEPSEEK_MODELS else DEEPSEEK_MODELS[0]
    else:
        for field in ("baseUrl", "model"):
            value = patch.get(field)
            if isinstance(value, str):
                ai[field] = value.strip()
            elif switching:
                ai[field] = ""
    key = patch.get("apiKey")
    if isinstance(key, str) and key.strip():
        ai["apiKey"] = key.strip()
    return ai

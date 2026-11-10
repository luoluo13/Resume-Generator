from __future__ import annotations

import json
import os
from pathlib import Path

VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / ".runtime"
LOG_DIR = RUNTIME_DIR / "logs"
DATA_DIR = ROOT / "data"
ASSETS_DIR = DATA_DIR / "assets"
BACKUPS_DIR = DATA_DIR / "backups"
EXPORTS_DIR = ROOT / "exports"
TEMPLATES_DIR = ROOT / "templates"
USER_TEMPLATES_DIR = DATA_DIR / "templates"
RESUMES_DIR = DATA_DIR / "resumes"
CHATS_DIR = DATA_DIR / "chats"
FRONTEND_DIST = ROOT / "frontend" / "dist"

# 无论通过 run.bat 还是直接启动服务，浏览器内核都固定使用项目内目录，避免写入用户目录
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(RUNTIME_DIR / "ms-playwright"))


def ensure_dirs() -> None:
    for folder in (
        RUNTIME_DIR,
        LOG_DIR,
        DATA_DIR,
        ASSETS_DIR,
        BACKUPS_DIR,
        EXPORTS_DIR,
        USER_TEMPLATES_DIR,
        RESUMES_DIR,
        CHATS_DIR,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def runtime_port() -> int:
    """端口由 run.bat 写入 runtime.json，同时通过环境变量传入，仅用于拼装导出地址。"""
    env_port = os.environ.get("RESUME_PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    config_file = RUNTIME_DIR / "runtime.json"
    if config_file.exists():
        try:
            return int(json.loads(config_file.read_text(encoding="utf-8")).get("port", 8765))
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    return 8765

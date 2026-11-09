from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import (
    DATA_DIR,
    EXPORTS_DIR,
    LOG_DIR,
    ROOT,
    VERSION,
    runtime_port,
)
from app.deps import registry
from app.services.exporter import chromium_ready
from app.services.fonts import font_state

router = APIRouter(tags=["system"])


class RevealRequest(BaseModel):
    path: str


@router.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "chromiumReady": chromium_ready(),
        "fontsReady": font_state()["ready"],
        "dataDir": str(DATA_DIR),
        "templates": len(registry.list()),
    }


@router.get("/api/system/info")
def system_info() -> dict:
    return {
        "version": VERSION,
        "port": runtime_port(),
        "root": str(ROOT),
        "dataDir": str(DATA_DIR),
        "exportsDir": str(EXPORTS_DIR),
        "logDir": str(LOG_DIR),
        "fonts": font_state(),
        "chromiumReady": chromium_ready(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }


@router.post("/api/system/reveal")
def reveal(payload: RevealRequest) -> dict:
    target = Path(payload.path).resolve()
    if not str(target).startswith(str(ROOT.resolve())) or not target.exists():
        raise HTTPException(status_code=400, detail="路径不在项目目录内")
    if target.is_file():
        subprocess.Popen(["explorer", "/select,", str(target)])
    else:
        os.startfile(str(target))
    return {"ok": True}

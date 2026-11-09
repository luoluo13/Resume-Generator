from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.deps import registry, store
from app.importers import ImportParseError, analyze_document, build_resume

router = APIRouter(prefix="/api/import", tags=["import"])

MAX_IMPORT_BYTES = 12 * 1024 * 1024


class ApplyPayload(BaseModel):
    basics: dict[str, Any] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    theme: dict[str, Any] = Field(default_factory=dict)
    sourceName: str = ""


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    name = file.filename or "resume"
    if not raw:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 12MB，请压缩后再试")
    try:
        draft = analyze_document(raw, name, registry)
    except ImportParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    draft["file"]["size"] = len(raw)
    return draft


@router.post("/apply")
def apply_import(payload: ApplyPayload) -> dict:
    current = store.load()
    try:
        data = build_resume(payload.model_dump(), current, registry)
    except ImportParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stamp = datetime.now().isoformat(timespec="seconds")
    meta = data.setdefault("meta", {})
    meta["createdAt"] = meta.get("createdAt") or stamp
    meta["updatedAt"] = stamp
    meta["importedAt"] = stamp
    if payload.sourceName:
        meta["importedFrom"] = payload.sourceName[:120]
    store.snapshot()
    store.save(data)
    return data

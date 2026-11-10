from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.deps import store
from app.models import Resume
from app.services.store import StoreError

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_IMPORT_BYTES = 5 * 1024 * 1024


@router.get("")
def read_resume() -> dict:
    try:
        return store.load()
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("")
def save_resume(payload: Resume) -> dict:
    data = payload.model_dump(mode="json")
    try:
        return {"savedAt": store.save(data)}
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import")
async def import_resume(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 5MB")
    try:
        return store.import_payload(raw)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export")
def export_json() -> Response:
    data = store.export_snapshot()
    name = store.active_name() or store.load().get("basics", {}).get("name") or "简历"
    filename = quote(f"{name}.json")
    return Response(
        content=data,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )

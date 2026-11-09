from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.deps import exporter, store
from app.services.exporter import ExportError

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    format: Literal["pdf", "png", "docx"]
    fileName: str | None = None


@router.post("")
async def run_export(payload: ExportRequest, request: Request) -> dict:
    resume = store.load()
    try:
        return await exporter.export(
            payload.format,
            resume,
            resume["theme"],
            str(request.base_url),
            payload.fileName,
        )
    except ExportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出失败：{exc}") from exc

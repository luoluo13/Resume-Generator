from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.config import TEMPLATES_DIR, USER_TEMPLATES_DIR
from app.deps import registry, store
from app.services.preview import TemplateError
from app.services.template_guard import TemplateGuardError
from app.services.template_pack import (
    TemplateConflictError,
    build_pack,
    build_prompt,
    delete_user_template,
    import_package,
)

router = APIRouter(tags=["templates"])


@router.get("/api/templates")
def list_templates() -> list[dict]:
    return registry.list()


@router.get("/api/templates/pack")
def download_pack() -> Response:
    data = build_pack(TEMPLATES_DIR)
    filename = quote("简历工坊-模板开发包.zip")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/api/templates/prompt", response_class=PlainTextResponse)
def template_prompt() -> PlainTextResponse:
    return PlainTextResponse(build_prompt(), media_type="text/plain; charset=utf-8")


@router.post("/api/templates/import")
async def import_template(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    builtin_ids = {item["id"] for item in registry.list() if item.get("source") == "builtin"}
    try:
        return import_package(raw, builtin_ids=builtin_ids, user_root=USER_TEMPLATES_DIR)
    except TemplateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TemplateGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/templates/{template_id}")
def remove_template(template_id: str) -> dict:
    builtin_ids = {item["id"] for item in registry.list() if item.get("source") == "builtin"}
    try:
        delete_user_template(USER_TEMPLATES_DIR, template_id, builtin_ids)
    except TemplateConflictError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TemplateGuardError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/api/preview", response_class=HTMLResponse)
def preview(
    template: str | None = Query(default=None),
    preview: int = Query(default=1),
) -> HTMLResponse:
    resume = store.load()
    try:
        html = registry.render(resume, template, for_preview=bool(preview))
    except TemplateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"模板渲染失败：{exc}") from exc
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "no-store, max-age=0"},
    )

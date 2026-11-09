from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import store
from app.services.chat_store import delete_sessions_for_resume
from app.services.store import StoreError

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


class ResumeCreate(BaseModel):
    name: str | None = Field(default=None, max_length=40)


class ResumeRename(BaseModel):
    name: str = Field(..., max_length=40)


@router.get("")
def list_resumes() -> dict:
    return {"items": store.list_resumes(), "activeId": store.active_id(), "activeName": store.active_name()}


@router.post("")
def create_resume(payload: ResumeCreate) -> dict:
    result = store.create(payload.name)
    return {**result, "items": store.list_resumes(), "activeId": result["id"], "activeName": result["name"]}


@router.post("/{resume_id}/activate")
def activate_resume(resume_id: str) -> dict:
    try:
        store.set_active(resume_id)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "activeId": resume_id, "activeName": store.active_name()}


@router.put("/{resume_id}")
def rename_resume(resume_id: str, payload: ResumeRename) -> dict:
    try:
        item = store.rename(resume_id, payload.name)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "item": item, "items": store.list_resumes()}


@router.delete("/{resume_id}")
def delete_resume(resume_id: str) -> dict:
    try:
        active_id = store.delete(resume_id)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    delete_sessions_for_resume(resume_id)
    return {"ok": True, "activeId": active_id, "items": store.list_resumes(), "activeName": store.active_name()}

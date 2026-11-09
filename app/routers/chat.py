from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.deps import store
from app.services import chat_store
from app.services.chat import ChatError, confirm_action, run_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatPayload(BaseModel):
    sessionId: str
    message: str


class SessionCreate(BaseModel):
    resumeId: str
    title: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    resumeId: str | None = None


class ConfirmPayload(BaseModel):
    id: str
    approve: bool = True
    sessionId: str | None = None


def _valid_resume(resume_id: str) -> bool:
    return any(item["id"] == resume_id for item in store.list_resumes())


@router.get("/sessions")
def list_sessions(resumeId: str | None = None) -> dict:
    return {"items": chat_store.list_sessions(resumeId)}


@router.post("/sessions")
def create_session(payload: SessionCreate) -> dict:
    if not _valid_resume(payload.resumeId):
        raise HTTPException(status_code=404, detail="找不到该简历")
    return chat_store.create_session(payload.resumeId, payload.title or "新会话")


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    try:
        return chat_store.get_session(session_id)
    except chat_store.ChatStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/sessions/{session_id}")
def update_session(session_id: str, payload: SessionUpdate) -> dict:
    if payload.resumeId and not _valid_resume(payload.resumeId):
        raise HTTPException(status_code=404, detail="找不到该简历")
    try:
        return chat_store.update_session(session_id, title=payload.title, resume_id=payload.resumeId)
    except chat_store.ChatStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    try:
        chat_store.delete_session(session_id)
    except chat_store.ChatStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("")
async def chat(payload: ChatPayload, request: Request) -> dict:
    try:
        session = chat_store.get_session(payload.sessionId)
    except chat_store.ChatStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    resume_id = str(session.get("resumeId") or "")
    if not _valid_resume(resume_id):
        raise HTTPException(status_code=400, detail="当前会话绑定的简历已不存在，请重新选择简历")

    history = [
        {"role": item["role"], "content": item["content"]}
        for item in session.get("messages", [])
        if item.get("role") in ("user", "assistant") and item.get("content")
    ]
    chat_store.append_messages(payload.sessionId, [{"role": "user", "content": payload.message}])

    try:
        result = await run_chat(history, payload.message, str(request.base_url), resume_id)
    except ChatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated = chat_store.append_messages(
        payload.sessionId,
        [{"role": "assistant", "content": result["reply"], "actions": result["actions"]}],
    )
    result["session"] = updated
    return result


@router.post("/confirm")
def confirm(payload: ConfirmPayload) -> dict:
    try:
        result = confirm_action(payload.id, payload.approve)
    except ChatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.sessionId:
        try:
            result["session"] = chat_store.append_messages(
                payload.sessionId,
                [{"role": "assistant", "content": result["message"], "actions": []}],
            )
        except chat_store.ChatStoreError:
            pass
    return result

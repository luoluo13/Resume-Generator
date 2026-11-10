from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.config import CHATS_DIR

_lock = threading.RLock()


class ChatStoreError(Exception):
    pass


def _stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _path(session_id: str) -> Path:
    if not session_id.startswith("chat_") or not session_id.replace("_", "").isalnum():
        raise ChatStoreError("会话标识不合法")
    return CHATS_DIR / f"{session_id}.json"


def _read(session_id: str) -> dict:
    file = _path(session_id)
    if not file.exists():
        raise ChatStoreError("会话不存在")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChatStoreError("会话记录已损坏") from exc
    if not isinstance(data, dict) or data.get("id") != session_id:
        raise ChatStoreError("会话记录已损坏")
    messages = data.get("messages")
    data["messages"] = [item for item in messages if isinstance(item, dict)] if isinstance(messages, list) else []
    return data


def _write(data: dict) -> None:
    file = _path(data["id"])
    temporary = file.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, file)
    except OSError as exc:
        raise ChatStoreError("会话记录保存失败，请检查磁盘空间") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _summary(session: dict) -> dict:
    messages = session.get("messages")
    if not isinstance(messages, list):
        messages = []
    preview = ""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        content = str(message.get("content") or "").strip()
        if content:
            preview = " ".join(content.split())[:48]
            break
    return {
        "id": session["id"],
        "title": str(session.get("title") or "新会话"),
        "resumeId": str(session.get("resumeId") or ""),
        "createdAt": str(session.get("createdAt") or ""),
        "updatedAt": str(session.get("updatedAt") or ""),
        "messageCount": len(messages),
        "preview": preview,
    }


def list_sessions(resume_id: str | None = None) -> list[dict]:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    with _lock:
        for file in CHATS_DIR.glob("chat_*.json"):
            try:
                session = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(session, dict) or not session.get("id"):
                continue
            if resume_id and session.get("resumeId") != resume_id:
                continue
            items.append(_summary(session))
    items.sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
    return items


def get_session(session_id: str) -> dict:
    with _lock:
        return _read(session_id)


def create_session(resume_id: str, title: str = "新会话") -> dict:
    now = _stamp()
    session = {
        "id": f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:5]}",
        "title": title.strip()[:30] or "新会话",
        "resumeId": resume_id,
        "messages": [],
        "createdAt": now,
        "updatedAt": now,
    }
    with _lock:
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
        _write(session)
    return session


def update_session(session_id: str, *, title: str | None = None, resume_id: str | None = None) -> dict:
    with _lock:
        session = _read(session_id)
        if title is not None:
            value = title.strip()[:30]
            session["title"] = value or session.get("title") or "新会话"
        if resume_id:
            session["resumeId"] = resume_id
        session["updatedAt"] = _stamp()
        _write(session)
        return session


def append_messages(session_id: str, messages: list[dict]) -> dict:
    with _lock:
        session = _read(session_id)
        for message in messages:
            content = str(message.get("content") or "")
            entry = {
                "id": str(message.get("id") or uuid.uuid4().hex[:12]),
                "role": message.get("role") if message.get("role") in ("user", "assistant") else "assistant",
                "content": content,
                "actions": message.get("actions") or [],
                "createdAt": str(message.get("createdAt") or _stamp()),
            }
            session["messages"].append(entry)
            if entry["role"] == "user" and session.get("title") in (None, "", "新会话"):
                title = " ".join(content.split())[:24]
                if title:
                    session["title"] = title
        session["updatedAt"] = _stamp()
        _write(session)
        return session


def delete_session(session_id: str) -> None:
    with _lock:
        _path(session_id).unlink(missing_ok=True)


def delete_sessions_for_resume(resume_id: str) -> None:
    with _lock:
        for summary in list_sessions(resume_id):
            try:
                delete_session(summary["id"])
            except ChatStoreError:
                continue

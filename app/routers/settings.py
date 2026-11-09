from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chat import test_connection
from app.services.settings import SettingsError, load_ai, merge_ai, public_ai, save_ai

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AiPayload(BaseModel):
    provider: str | None = None
    baseUrl: str | None = None
    model: str | None = None
    apiKey: str | None = None
    clearKey: bool = False


@router.get("/ai")
def get_ai_settings() -> dict[str, Any]:
    return public_ai(load_ai())


@router.put("/ai")
def update_ai_settings(payload: AiPayload) -> dict[str, Any]:
    try:
        return public_ai(save_ai(payload.model_dump()))
    except SettingsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/test")
def test_ai_settings(payload: AiPayload) -> dict[str, Any]:
    return test_connection(merge_ai(payload.model_dump()))

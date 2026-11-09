from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps

from app.config import ASSETS_DIR

router = APIRouter(prefix="/api/assets", tags=["assets"])

MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="照片超过 5MB")
    if file.content_type and file.content_type not in ALLOWED:
        raise HTTPException(status_code=415, detail="仅支持 JPG / PNG / WEBP")
    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="图片无法解析") from exc

    image.thumbnail((600, 600), Image.LANCZOS)
    digest = hashlib.sha1(raw).hexdigest()[:10]
    name = f"photo-{digest}.jpg"
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image.save(ASSETS_DIR / name, format="JPEG", quality=90, optimize=True)
    return {"path": f"assets/{name}", "url": f"/media/assets/{name}"}

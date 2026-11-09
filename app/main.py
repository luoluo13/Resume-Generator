from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import DATA_DIR, FRONTEND_DIST, VERSION, ensure_dirs, runtime_port
from app.routers import assets, chat, export, resume, resumes, settings, system, templates

ensure_dirs()

app = FastAPI(title="简历工坊 Resume Studio", version=VERSION, docs_url=None, redoc_url=None)

app.include_router(system.router)
app.include_router(resume.router)
app.include_router(resumes.router)
app.include_router(chat.router)
app.include_router(settings.router)
app.include_router(assets.router)
app.include_router(templates.router)
app.include_router(export.router)

app.mount("/media", StaticFiles(directory=str(DATA_DIR)), name="media")

PORT = runtime_port()


@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
        host = request.headers.get("host", "")
        allowed = {
            f"http://{host}",
            f"https://{host}",
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        }
        if origin not in allowed:
            return JSONResponse({"code": "forbidden", "message": "非法来源"}, status_code=403)
    return await call_next(request)


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"code": "not_found", "message": "接口不存在"}, status_code=404)
    if not FRONTEND_DIST.exists():
        return HTMLResponse(
            "<meta charset='utf-8'><h1>前端资源缺失</h1>"
            "<p>请先运行 build_frontend.bat 构建前端，或使用完整发布包。</p>",
            status_code=503,
        )
    candidate = (FRONTEND_DIST / full_path).resolve()
    if full_path and candidate.is_file() and str(candidate).startswith(str(FRONTEND_DIST.resolve())):
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIST / "index.html")

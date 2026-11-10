from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from app.config import DATA_DIR, RUNTIME_DIR
from app.exporters.docx import export_docx
from app.exporters.pdf import export_pdf
from app.exporters.png import export_png

ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|\r\n\t]+')


class ExportError(Exception):
    pass


def sanitize_filename(name: str) -> str:
    cleaned = ILLEGAL_FILENAME.sub("-", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80] or "简历"


def chromium_ready() -> bool:
    root = RUNTIME_DIR / "ms-playwright"
    if not root.exists():
        return False
    full = any((path / "chrome-win" / "chrome.exe").is_file() for path in root.glob("chromium-*"))
    shell = any(
        (path / "chrome-win" / "headless_shell.exe").is_file()
        for path in root.glob("chromium_headless_shell-*")
    )
    return full and shell


class ExportService:
    def __init__(self, exports_dir: Path, data_dir: Path) -> None:
        self.exports_dir = exports_dir
        self.data_dir = data_dir
        self._lock = asyncio.Lock()

    def _target(self, base: str, suffix: str) -> Path:
        candidate = self.exports_dir / f"{base}{suffix}"
        index = 2
        while candidate.exists():
            candidate = self.exports_dir / f"{base}-{index}{suffix}"
            index += 1
        return candidate

    def _photo(self, resume: dict) -> Path | None:
        photo = resume.get("basics", {}).get("photo")
        if not photo:
            return None
        path = (self.data_dir / photo).resolve()
        if path.is_file() and path.is_relative_to(self.data_dir.resolve()):
            return path
        return None

    async def export(self, fmt: str, resume: dict, theme: dict, base_url: str, file_name: str | None = None) -> dict:
        if not chromium_ready() and fmt in ("pdf", "png"):
            raise ExportError("浏览器内核尚未就绪，请重新运行 run.bat 补齐环境")

        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        name = resume.get("basics", {}).get("name") or "简历"
        intent = resume.get("basics", {}).get("jobIntention") or ""
        default_name = "_".join(part for part in (name, intent, stamp) if part)
        base = sanitize_filename(file_name or default_name)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        template_id = quote(theme.get("template", "classic"), safe="")
        url = f"{base_url.rstrip('/')}/api/preview?template={template_id}&preview=0"

        async with self._lock:
            try:
                return await asyncio.wait_for(
                    self._run(fmt, resume, theme, url, base),
                    timeout=120,
                )
            except asyncio.TimeoutError as exc:
                raise ExportError("导出超时，请稍后重试") from exc

    async def _run(self, fmt: str, resume: dict, theme: dict, url: str, base: str) -> dict:
        if fmt == "pdf":
            output = self._target(base, ".pdf")
            await export_pdf(url, output)
            files = [output]
        elif fmt == "png":
            output = self._target(base, ".png")
            files = await export_png(url, output)
        elif fmt == "docx":
            output = self._target(base, ".docx")
            export_docx(resume, theme, output, self._photo(resume))
            files = [output]
        else:
            raise ExportError(f"不支持的导出格式：{fmt}")

        return {
            "dir": str(self.exports_dir),
            "files": [
                {"name": path.name, "path": str(path), "size": path.stat().st_size}
                for path in files
            ],
        }

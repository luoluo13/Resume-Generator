from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.config import RUNTIME_DIR
from app.importers.base import ImportParseError


def _soffice_candidates() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    candidates = [
        program_files / "LibreOffice" / "program" / "soffice.exe",
        program_files_x86 / "LibreOffice" / "program" / "soffice.exe",
        Path(r"D:\Program Files\LibreOffice\program\soffice.exe"),
    ]
    found = shutil.which("soffice")
    if found:
        candidates.insert(0, Path(found))
    return [path for path in candidates if path.is_file()]


def _creation_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _convert_with_libreoffice(source: Path, target: Path) -> bool:
    for executable in _soffice_candidates():
        try:
            subprocess.run(
                [str(executable), "--headless", "--convert-to", "docx", "--outdir", str(target.parent), str(source)],
                timeout=90,
                capture_output=True,
                creationflags=_creation_flags(),
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if target.is_file():
            return True
    return False


def _convert_with_word(source: Path, target: Path) -> bool:
    if os.name != "nt":
        return False
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    script = (
        "$ErrorActionPreference='Stop';"
        "$word=New-Object -ComObject Word.Application;"
        "$word.Visible=$false;"
        "$word.DisplayAlerts=0;"
        "try {"
        f"$doc=$word.Documents.Open({quote(source)}, $false, $true);"
        f"$doc.SaveAs2({quote(target)}, 16);"
        "$doc.Close($false);"
        "} finally { $word.Quit() }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            timeout=120,
            capture_output=True,
            creationflags=_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return target.is_file()


def convert_doc(raw: bytes) -> bytes:
    """把旧版 .doc 转换为 docx，优先 LibreOffice，其次本机 Word。"""
    workdir = RUNTIME_DIR / "temp" / f"doc-import-{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    source = workdir / "source.doc"
    target = workdir / "source.docx"
    try:
        source.write_bytes(raw)
        if _convert_with_libreoffice(source, target) or _convert_with_word(source, target):
            return target.read_bytes()
        raise ImportParseError(
            "无法转换 .doc 文件。请用 Word 或 WPS 打开后另存为 .docx，再重新导入；也可以直接导入 PDF。"
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

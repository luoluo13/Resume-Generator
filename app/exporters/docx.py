from __future__ import annotations

import importlib.util
from pathlib import Path

from app.config import TEMPLATES_DIR
from app.exporters.docx_base import build_document

GENERIC_PROFILE = {
    "layout": "single",
    "section_style": "rule",
    "section_en": True,
    "numbered": False,
    "dense": False,
    "bullet": "dot",
    "serif": False,
}


def _load_builder(template_id: str):
    module_file = TEMPLATES_DIR / template_id / "docx_builder.py"
    if not module_file.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"docx_builder_{template_id}", module_file)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_docx(resume: dict, theme: dict, output: Path, photo: Path | None) -> Path:
    builder = _load_builder(theme.get("template", "classic"))
    if builder is None:
        document = build_document(resume, theme, GENERIC_PROFILE, photo)
    else:
        document = builder.build(resume, theme, photo)
    document.save(str(output))
    return output

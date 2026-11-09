from __future__ import annotations

from app.config import (
    ASSETS_DIR,
    DATA_DIR,
    EXPORTS_DIR,
    TEMPLATES_DIR,
    USER_TEMPLATES_DIR,
)
from app.services.exporter import ExportService
from app.services.preview import TemplateRegistry
from app.services.store import ResumeStore

store = ResumeStore(DATA_DIR)
registry = TemplateRegistry([TEMPLATES_DIR, USER_TEMPLATES_DIR])
exporter = ExportService(EXPORTS_DIR, ASSETS_DIR.parent)

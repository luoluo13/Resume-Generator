from __future__ import annotations

from app.config import (
    ASSETS_DIR,
    BACKUPS_DIR,
    EXPORTS_DIR,
    RESUME_BACKUP,
    RESUME_FILE,
    TEMPLATES_DIR,
    USER_TEMPLATES_DIR,
)
from app.services.exporter import ExportService
from app.services.preview import TemplateRegistry
from app.services.store import ResumeStore

store = ResumeStore(RESUME_FILE, RESUME_BACKUP, BACKUPS_DIR)
registry = TemplateRegistry([TEMPLATES_DIR, USER_TEMPLATES_DIR])
exporter = ExportService(EXPORTS_DIR, ASSETS_DIR.parent)

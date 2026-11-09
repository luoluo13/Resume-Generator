from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.models import Resume
from app.services.sample import sample_resume


class StoreError(Exception):
    pass


class ResumeStore:
    """简历 JSON 的原子读写与备份轮转。"""

    def __init__(self, file: Path, backup: Path, backups_dir: Path) -> None:
        self.file = file
        self.backup = backup
        self.backups_dir = backups_dir

    def load(self) -> dict:
        if not self.file.exists():
            data = sample_resume()
            self.save(data)
            return data
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if self.backup.exists():
                data = json.loads(self.backup.read_text(encoding="utf-8"))
                self._copy_corrupt()
                self.save(data)
                return data
            self._copy_corrupt()
            data = sample_resume()
            self.save(data)
            return data

    def save(self, data: dict) -> str:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        if self.file.exists():
            try:
                shutil.copyfile(self.file, self.backup)
            except OSError:
                pass
        tmp = self.file.with_suffix(".tmp")
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, self.file)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        return datetime.now().isoformat(timespec="seconds")

    def import_payload(self, raw: bytes) -> dict:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("文件不是有效的 JSON") from exc
        try:
            resume = Resume.model_validate(data)
        except Exception as exc:  # pydantic ValidationError
            raise StoreError(f"数据结构不符合要求：{exc}") from exc
        self._snapshot()
        normalized = resume.model_dump(mode="json")
        self.save(normalized)
        return normalized

    def export_snapshot(self) -> str:
        return json.dumps(self.load(), ensure_ascii=False, indent=2)

    def snapshot(self) -> None:
        self._snapshot()

    def _snapshot(self) -> None:
        if not self.file.exists():
            return
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copyfile(self.file, self.backups_dir / f"resume-{stamp}.json")
        snapshots = sorted(self.backups_dir.glob("resume-*.json"))
        for old in snapshots[:-20]:
            old.unlink(missing_ok=True)

    def _copy_corrupt(self) -> None:
        if not self.file.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            shutil.copyfile(self.file, self.backups_dir / f"corrupt-{stamp}.json")
        except OSError:
            pass

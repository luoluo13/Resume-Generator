from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.models import Resume
from app.services.sample import blank_resume, sample_resume


class StoreError(Exception):
    pass


def _stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _name_from(data: dict, fallback: str) -> str:
    person = str(data.get("basics", {}).get("name") or "").strip()
    return f"{person}的简历" if person else fallback


class ResumeStore:
    """多份简历的原子读写、命名管理与备份轮转。"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.dir = data_dir / "resumes"
        self.index_file = self.dir / "index.json"
        self.backups_dir = data_dir / "backups"
        self.legacy_file = data_dir / "resume.json"
        self.legacy_backup = data_dir / "resume.json.bak"
        self._lock = threading.RLock()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if not self.index_file.exists():
                self._bootstrap()

    # ---------- 索引 ----------

    def _read_index(self) -> dict:
        try:
            data = json.loads(self.index_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        items = [item for item in data.get("items", []) if isinstance(item, dict) and item.get("id")]
        active = data.get("activeId")
        if not items:
            self._bootstrap()
            return self._read_index()
        if active not in {item["id"] for item in items}:
            active = items[0]["id"]
        return {"activeId": active, "items": items}

    def _write_index(self, data: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        temporary = self.index_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.index_file)

    def _file(self, resume_id: str) -> Path:
        return self.dir / f"{resume_id}.json"

    def _backup_file(self, resume_id: str) -> Path:
        return self.dir / f"{resume_id}.bak.json"

    def _unique_name(self, base: str, items: list[dict]) -> str:
        names = {str(item.get("name") or "") for item in items}
        if base not in names:
            return base
        index = 2
        while f"{base} {index}" in names:
            index += 1
        return f"{base} {index}"

    def _bootstrap(self) -> None:
        now = _stamp()
        resume_id = f"resume_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data: dict | None = None
        if self.legacy_file.exists():
            try:
                candidate = json.loads(self.legacy_file.read_text(encoding="utf-8"))
                data = Resume.model_validate(candidate).model_dump(mode="json")
            except Exception:  # noqa: BLE001 迁移失败时退回示例数据
                data = None
        if data is None:
            data = sample_resume()
        data["id"] = resume_id
        meta = data.setdefault("meta", {})
        meta.setdefault("createdAt", now)
        meta["updatedAt"] = now
        item = {
            "id": resume_id,
            "name": _name_from(data, "我的简历"),
            "createdAt": now,
            "updatedAt": now,
        }
        self._write_resume(resume_id, data)
        self._write_index({"activeId": resume_id, "items": [item]})
        if self.legacy_file.exists():
            archive = self.data_dir / "resume.legacy.json"
            try:
                os.replace(self.legacy_file, archive)
            except OSError:
                pass
        if self.legacy_backup.exists():
            try:
                os.replace(self.legacy_backup, self.data_dir / "resume.legacy.json.bak")
            except OSError:
                pass

    # ---------- 查询 ----------

    def list_resumes(self) -> list[dict]:
        with self._lock:
            index = self._read_index()
            items = []
            for item in index["items"]:
                try:
                    data = self._read_resume(item["id"])
                except StoreError:
                    continue
                items.append(
                    {
                        "id": item["id"],
                        "name": str(item.get("name") or "未命名简历"),
                        "personName": str(data.get("basics", {}).get("name") or ""),
                        "createdAt": str(item.get("createdAt") or ""),
                        "updatedAt": str(item.get("updatedAt") or data.get("meta", {}).get("updatedAt") or ""),
                        "sectionCount": len(data.get("sections", [])),
                        "active": item["id"] == index["activeId"],
                    }
                )
            return items

    def active_id(self) -> str:
        with self._lock:
            return self._read_index()["activeId"]

    def active_name(self) -> str:
        with self._lock:
            index = self._read_index()
            for item in index["items"]:
                if item["id"] == index["activeId"]:
                    return str(item.get("name") or "我的简历")
            return "我的简历"

    def set_active(self, resume_id: str) -> None:
        with self._lock:
            index = self._read_index()
            if resume_id not in {item["id"] for item in index["items"]}:
                raise StoreError("找不到该简历")
            index["activeId"] = resume_id
            self._write_index(index)

    # ---------- 读写 ----------

    def _read_resume(self, resume_id: str) -> dict:
        file = self._file(resume_id)
        if not file.exists():
            raise StoreError("找不到该简历")
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            backup = self._backup_file(resume_id)
            if backup.exists():
                try:
                    data = json.loads(backup.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise StoreError("简历数据已损坏") from exc
                self._write_resume(resume_id, data)
            else:
                raise StoreError("简历数据已损坏")
        data["id"] = resume_id
        return data

    def _write_resume(self, resume_id: str, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        file = self._file(resume_id)
        if file.exists():
            try:
                shutil.copyfile(file, self._backup_file(resume_id))
            except OSError:
                pass
        temporary = file.with_suffix(".tmp")
        try:
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, file)
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)

    def load(self, resume_id: str | None = None) -> dict:
        with self._lock:
            rid = resume_id or self._read_index()["activeId"]
            try:
                return self._read_resume(rid)
            except StoreError:
                if resume_id:
                    raise
                data = sample_resume()
                data["id"] = rid
                self._write_resume(rid, data)
                return data

    def save(self, data: dict, resume_id: str | None = None) -> str:
        with self._lock:
            index = self._read_index()
            rid = resume_id or str(data.get("id") or index["activeId"])
            if rid not in {item["id"] for item in index["items"]}:
                now = _stamp()
                index["items"].append(
                    {"id": rid, "name": _name_from(data, "未命名简历"), "createdAt": now, "updatedAt": now}
                )
            stamp = _stamp()
            data["id"] = rid
            meta = data.setdefault("meta", {})
            meta.setdefault("createdAt", stamp)
            meta["updatedAt"] = stamp
            self._write_resume(rid, data)
            for item in index["items"]:
                if item["id"] == rid:
                    item["updatedAt"] = stamp
                    break
            index["activeId"] = rid
            self._write_index(index)
            return stamp

    def create(self, name: str | None = None) -> dict:
        with self._lock:
            index = self._read_index()
            resume_id = f"resume_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}"
            data = blank_resume()
            data["id"] = resume_id
            now = _stamp()
            data["meta"] = {"createdAt": now, "updatedAt": now}
            default_name = self._unique_name((name or "").strip()[:40] or "未命名简历", index["items"])
            index["items"].append(
                {"id": resume_id, "name": default_name, "createdAt": now, "updatedAt": now}
            )
            index["activeId"] = resume_id
            self._write_resume(resume_id, data)
            self._write_index(index)
            return {
                "id": resume_id,
                "name": default_name,
                "resume": data,
            }

    def rename(self, resume_id: str, name: str) -> dict:
        title = (name or "").strip()[:40]
        if not title:
            raise StoreError("简历名称不能为空")
        with self._lock:
            index = self._read_index()
            for item in index["items"]:
                if item["id"] == resume_id:
                    item["name"] = title
                    item["updatedAt"] = _stamp()
                    self._write_index(index)
                    return item
            raise StoreError("找不到该简历")

    def delete(self, resume_id: str) -> str:
        with self._lock:
            index = self._read_index()
            if len(index["items"]) <= 1:
                raise StoreError("至少需要保留一份简历")
            remaining = [item for item in index["items"] if item["id"] != resume_id]
            if len(remaining) == len(index["items"]):
                raise StoreError("找不到该简历")
            index["items"] = remaining
            if index["activeId"] == resume_id:
                index["activeId"] = remaining[0]["id"]
            self._file(resume_id).unlink(missing_ok=True)
            self._backup_file(resume_id).unlink(missing_ok=True)
            self._write_index(index)
            return index["activeId"]

    # ---------- 导入导出与快照 ----------

    def import_payload(self, raw: bytes) -> dict:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("文件不是有效的 JSON") from exc
        try:
            resume = Resume.model_validate(data)
        except Exception as exc:  # pydantic ValidationError
            raise StoreError(f"数据结构不符合要求：{exc}") from exc
        self.snapshot()
        normalized = resume.model_dump(mode="json")
        self.save(normalized)
        return normalized

    def export_snapshot(self) -> str:
        return json.dumps(self.load(), ensure_ascii=False, indent=2)

    def snapshot(self, resume_id: str | None = None) -> None:
        with self._lock:
            rid = resume_id or self._read_index()["activeId"]
            file = self._file(rid)
            if not file.exists():
                return
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = self.backups_dir / f"resume-{rid}-{stamp}.json"
            shutil.copyfile(file, target)
            snapshots = sorted(self.backups_dir.glob(f"resume-{rid}-*.json"))
            for old in snapshots[:-20]:
                old.unlink(missing_ok=True)

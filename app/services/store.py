from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.models import Resume
from app.services.sample import blank_resume, sample_resume

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class StoreError(Exception):
    pass


def _check_id(resume_id: str) -> str:
    value = str(resume_id or "").strip()
    if not _ID_RE.fullmatch(value):
        raise StoreError("简历标识不合法")
    return value


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
        raw_items = data.get("items") if isinstance(data, dict) else None
        items: list[dict] = []
        for item in raw_items if isinstance(raw_items, list) else []:
            if not isinstance(item, dict):
                continue
            resume_id = str(item.get("id") or "")
            if not _ID_RE.fullmatch(resume_id):
                continue
            items.append({**item, "id": resume_id})
        active = data.get("activeId") if isinstance(data, dict) else None
        if not items:
            items = self._scan_items()
            if items:
                active = items[0]["id"]
                try:
                    self._write_index({"activeId": active, "items": items})
                except OSError:
                    pass
                return {"activeId": active, "items": items}
            self._bootstrap()
            return self._read_index()
        if active not in {item["id"] for item in items}:
            active = items[0]["id"]
        return {"activeId": active, "items": items}

    def _scan_items(self) -> list[dict]:
        """索引损坏时，从目录中现有的简历文件重建列表。"""
        items: list[dict] = []
        for file in sorted(self.dir.glob("*.json")):
            if file.name == "index.json" or file.name.endswith(".bak.json"):
                continue
            if not _ID_RE.fullmatch(file.stem):
                continue
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
            items.append(
                {
                    "id": file.stem,
                    "name": _name_from(data, "未命名简历"),
                    "createdAt": str(meta.get("createdAt") or ""),
                    "updatedAt": str(meta.get("updatedAt") or ""),
                }
            )
        return items

    def _write_index(self, data: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        temporary = self.index_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.index_file)

    def _file(self, resume_id: str) -> Path:
        return self.dir / f"{_check_id(resume_id)}.json"

    def _backup_file(self, resume_id: str) -> Path:
        return self.dir / f"{_check_id(resume_id)}.bak.json"

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
            if not isinstance(data, dict):
                raise ValueError("resume is not an object")
        except (OSError, json.JSONDecodeError, ValueError):
            backup = self._backup_file(resume_id)
            if backup.exists():
                try:
                    data = json.loads(backup.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        raise ValueError("resume is not an object")
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    raise StoreError("简历数据已损坏") from exc
                # 用备份恢复时不覆盖备份，避免损坏数据污染存档
                self._write_resume(resume_id, data, backup=False)
            else:
                raise StoreError("简历数据已损坏")
        data["id"] = resume_id
        return data

    @staticmethod
    def _valid_file(file: Path) -> bool:
        try:
            return isinstance(json.loads(file.read_text(encoding="utf-8")), dict)
        except (OSError, json.JSONDecodeError):
            return False

    def _write_resume(self, resume_id: str, data: dict, backup: bool = True) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        file = self._file(resume_id)
        if backup and file.exists() and self._valid_file(file):
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
            index = self._read_index()
            rid = _check_id(resume_id) if resume_id else index["activeId"]
            try:
                return self._read_resume(rid)
            except StoreError:
                if resume_id:
                    raise
                # 当前简历不可读时切换到其他可读简历，避免用示例数据覆盖用户内容
                for item in index["items"]:
                    if item["id"] == rid:
                        continue
                    try:
                        data = self._read_resume(item["id"])
                    except StoreError:
                        continue
                    index["activeId"] = item["id"]
                    try:
                        self._write_index(index)
                    except OSError:
                        pass
                    return data
                raise StoreError("简历数据已损坏，请从 data/backups 恢复") from None

    def save(self, data: dict, resume_id: str | None = None) -> str:
        with self._lock:
            index = self._read_index()
            if resume_id:
                rid = _check_id(resume_id)
            else:
                candidate = str(data.get("id") or "").strip()
                rid = (
                    candidate
                    if _ID_RE.fullmatch(candidate)
                    else f"resume_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}"
                )
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
            rid = _check_id(resume_id)
            index = self._read_index()
            if len(index["items"]) <= 1:
                raise StoreError("至少需要保留一份简历")
            remaining = [item for item in index["items"] if item["id"] != rid]
            if len(remaining) == len(index["items"]):
                raise StoreError("找不到该简历")
            index["items"] = remaining
            if index["activeId"] == rid:
                index["activeId"] = remaining[0]["id"]
            # 先落盘索引，再清理文件；文件残留不影响使用，索引丢失才致命
            self._write_index(index)
            for path in (self._file(rid), self._backup_file(rid)):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
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

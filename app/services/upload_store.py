from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.services.document_loader import SUPPORTED_EXTENSIONS, extract_pdf_text


@dataclass(slots=True)
class UploadRecord:
    file_id: str
    file_name: str
    stored_name: str
    status: str
    source_path: str
    updated_at: str


class UploadStore:
    def __init__(self, uploads_dir: Path, manifest_path: Path) -> None:
        self.uploads_dir = uploads_dir
        self.manifest_path = manifest_path
        self._lock = threading.Lock()
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self._write_records([])

    def list_uploads(self) -> list[UploadRecord]:
        return [UploadRecord(**item) for item in self._read_records()]

    def create_upload(self, file_name: str, content: bytes) -> UploadRecord:
        self._ensure_supported(file_name, content)
        record = UploadRecord(
            file_id=str(uuid4()),
            file_name=file_name,
            stored_name=f"{uuid4().hex}{Path(file_name).suffix.lower()}",
            status="ready",
            source_path="",
            updated_at=self._now_iso(),
        )
        record.source_path = self._write_file(record.stored_name, content)
        with self._lock:
            records = self._read_records()
            records.append(asdict(record))
            self._write_records(records)
        return record

    def replace_upload(self, file_id: str, file_name: str, content: bytes) -> UploadRecord:
        self._ensure_supported(file_name, content)
        with self._lock:
            records = self._read_records()
            for item in records:
                if item["file_id"] == file_id:
                    old_file = self.uploads_dir / item["stored_name"]
                    if old_file.exists():
                        old_file.unlink()
                    item["file_name"] = file_name
                    item["stored_name"] = f"{uuid4().hex}{Path(file_name).suffix.lower()}"
                    item["source_path"] = self._write_file(item["stored_name"], content)
                    item["updated_at"] = self._now_iso()
                    self._write_records(records)
                    return UploadRecord(**item)
        raise KeyError(file_id)

    def delete_upload(self, file_id: str) -> None:
        with self._lock:
            records = self._read_records()
            remaining: list[dict[str, str]] = []
            deleted = False
            for item in records:
                if item["file_id"] == file_id:
                    deleted = True
                    file_path = self.uploads_dir / item["stored_name"]
                    if file_path.exists():
                        file_path.unlink()
                    continue
                remaining.append(item)
            if not deleted:
                raise KeyError(file_id)
            self._write_records(remaining)

    def _ensure_supported(self, file_name: str, content: bytes) -> None:
        suffix = Path(file_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")
        if suffix == ".pdf":
            extract_pdf_text(content, file_name)

    def _write_file(self, stored_name: str, content: bytes) -> str:
        file_path = self.uploads_dir / stored_name
        file_path.write_bytes(content)
        return file_path.as_posix()

    def _read_records(self) -> list[dict[str, str]]:
        if not self.manifest_path.exists():
            return []
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _write_records(self, records: list[dict[str, str]] | list[dict[str, object]]) -> None:
        self.manifest_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

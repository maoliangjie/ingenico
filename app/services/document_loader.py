from __future__ import annotations

import hashlib
import json
from pathlib import Path

from langchain_core.documents import Document


SUPPORTED_EXTENSIONS = {".txt", ".md", ".json"}


def discover_source_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted(
        path
        for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def flatten_json(payload: object, prefix: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(flatten_json(value, next_prefix))
        return lines

    if isinstance(payload, list):
        for index, value in enumerate(payload):
            next_prefix = f"{prefix}[{index}]"
            lines.extend(flatten_json(value, next_prefix))
        return lines

    value = "null" if payload is None else str(payload)
    label = prefix or "value"
    lines.append(f"{label}: {value}")
    return lines


def load_documents(data_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in discover_source_files(data_dir):
        relative_path = path.relative_to(data_dir).as_posix()
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            content = "\n".join(flatten_json(payload))
        else:
            content = path.read_text(encoding="utf-8").strip()

        if not content:
            continue

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": relative_path,
                    "file_name": path.name,
                    "file_type": path.suffix.lower().lstrip("."),
                },
            )
        )
    return documents


def compute_data_fingerprint(data_dir: Path) -> dict[str, object]:
    files = discover_source_files(data_dir)
    digest = hashlib.sha256()
    file_entries: list[dict[str, str | int]] = []

    for path in files:
        relative_path = path.relative_to(data_dir).as_posix()
        content = path.read_bytes()
        digest.update(relative_path.encode("utf-8"))
        digest.update(content)
        file_entries.append(
            {
                "path": relative_path,
                "size": len(content),
            }
        )

    return {
        "fingerprint": digest.hexdigest(),
        "files": file_entries,
        "document_count": len(files),
    }


def load_manifest(manifest_path: Path) -> dict[str, object] | None:
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def write_manifest(manifest_path: Path, manifest: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

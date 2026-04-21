from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document


SUPPORTED_EXTENSIONS = {".txt", ".md", ".json"}


@dataclass(frozen=True, slots=True)
class SourceDirectory:
    name: str
    root: Path
    scope: str


def discover_source_files(source: SourceDirectory) -> list[Path]:
    if not source.root.exists():
        return []
    return sorted(
        path
        for path in source.root.rglob("*")
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


def load_documents_from_sources(sources: list[SourceDirectory]) -> list[Document]:
    documents: list[Document] = []
    for source in sources:
        for path in discover_source_files(source):
            relative_path = path.relative_to(source.root).as_posix()
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
                        "scope": source.scope,
                        "source_directory": source.name,
                    },
                )
            )
    return documents


def compute_sources_fingerprint(sources: list[SourceDirectory]) -> dict[str, object]:
    digest = hashlib.sha256()
    file_entries: list[dict[str, str | int]] = []
    document_count = 0

    for source in sources:
        for path in discover_source_files(source):
            relative_path = path.relative_to(source.root).as_posix()
            content = path.read_bytes()
            digest.update(source.scope.encode("utf-8"))
            digest.update(relative_path.encode("utf-8"))
            digest.update(content)
            file_entries.append(
                {
                    "scope": source.scope,
                    "path": relative_path,
                    "size": len(content),
                }
            )
            document_count += 1

    return {
        "fingerprint": digest.hexdigest(),
        "files": file_entries,
        "document_count": document_count,
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

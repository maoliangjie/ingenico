from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError


LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".pdf"}


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


def extract_pdf_text(pdf_bytes: bytes, file_name: str = "<memory>") -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except PdfReadError as exc:
        raise ValueError(f"PDF '{file_name}' could not be read: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive adapter around library errors
        raise ValueError(f"PDF '{file_name}' could not be parsed: {exc}") from exc

    if reader.is_encrypted:
        raise ValueError(f"PDF '{file_name}' is encrypted and cannot be indexed.")

    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(text)

    combined = "\n\n".join(parts).strip()
    if not combined:
        raise ValueError(f"PDF '{file_name}' does not contain extractable text.")
    return combined


def load_documents_from_sources(sources: list[SourceDirectory]) -> list[Document]:
    documents: list[Document] = []
    for source in sources:
        for path in discover_source_files(source):
            relative_path = path.relative_to(source.root).as_posix()
            try:
                content = _load_source_content(path)
            except ValueError as exc:
                if path.suffix.lower() == ".pdf":
                    LOGGER.warning(
                        "Skipping PDF source '%s' from %s: %s",
                        relative_path,
                        source.scope,
                        exc,
                    )
                    continue
                raise

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


def _load_source_content(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return "\n".join(flatten_json(payload))
    if suffix == ".pdf":
        return extract_pdf_text(path.read_bytes(), path.name)
    return path.read_text(encoding="utf-8").strip()

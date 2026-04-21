from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


@dataclass(slots=True)
class Settings:
    openai_api_key: str
    openai_api_base: str | None
    chat_model: str
    embedding_provider: str
    openai_embedding_model: str
    local_embedding_model: str
    local_embedding_device: str
    data_dir: Path
    storage_dir: Path
    uploads_dir: Path
    upload_manifest_path: Path
    vector_dir: Path
    manifest_path: Path
    redis_url: str
    redis_prefix: str
    redis_cache_ttl_seconds: int
    collection_name: str
    default_top_k: int
    history_window: int
    chunk_size: int
    chunk_overlap: int
    frontend_dist_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        storage_dir = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "storage")).resolve()
        data_dir = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data")).resolve()
        uploads_dir = Path(os.getenv("RAG_UPLOADS_DIR", storage_dir / "uploads")).resolve()
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local").strip().lower(),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            local_embedding_model=os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            local_embedding_device=os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu"),
            data_dir=data_dir,
            storage_dir=storage_dir,
            uploads_dir=uploads_dir,
            upload_manifest_path=storage_dir / "uploads.json",
            vector_dir=storage_dir / "chroma",
            manifest_path=storage_dir / "index_manifest.json",
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            redis_prefix=os.getenv("REDIS_PREFIX", "ingenico"),
            redis_cache_ttl_seconds=_int_env("REDIS_CACHE_TTL_SECONDS", 3600),
            collection_name=os.getenv("RAG_COLLECTION_NAME", "knowledge_base"),
            default_top_k=_int_env("RAG_DEFAULT_TOP_K", 4),
            history_window=_int_env("RAG_HISTORY_WINDOW", 6),
            chunk_size=_int_env("RAG_CHUNK_SIZE", 900),
            chunk_overlap=_int_env("RAG_CHUNK_OVERLAP", 180),
            frontend_dist_dir=Path(os.getenv("FRONTEND_DIST_DIR", BASE_DIR / "frontend" / "dist")).resolve(),
        )

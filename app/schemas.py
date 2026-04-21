from __future__ import annotations

from pydantic import BaseModel, Field


class SourceSnippet(BaseModel):
    source: str
    file_name: str
    content: str
    score: float | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    session_id: str | None = Field(default=None, min_length=1, max_length=255)
    top_k: int | None = Field(default=None, ge=1, le=10)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceSnippet]
    cache_hit: bool = False


class UploadRecord(BaseModel):
    file_id: str
    file_name: str
    stored_name: str
    status: str
    source_path: str
    updated_at: str


class UploadListResponse(BaseModel):
    files: list[UploadRecord]


class HealthResponse(BaseModel):
    status: str
    ready: bool
    document_count: int
    chunk_count: int
    fingerprint: str | None = None
    redis_ready: bool = False
    upload_count: int = 0
    startup_error: str | None = None

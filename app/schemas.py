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


class HealthResponse(BaseModel):
    status: str
    ready: bool
    document_count: int
    chunk_count: int
    fingerprint: str | None = None
    startup_error: str | None = None

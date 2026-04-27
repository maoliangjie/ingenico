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


class ToolCall(BaseModel):
    tool_name: str
    status: str
    grounding_type: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result_preview: str
    payload: dict[str, object] | list[object] | str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceSnippet]
    cache_hit: bool = False
    tool_calls: list[ToolCall] = Field(default_factory=list)


class UploadRecord(BaseModel):
    file_id: str
    file_name: str
    stored_name: str
    status: str
    source_path: str
    updated_at: str


class UploadListResponse(BaseModel):
    files: list[UploadRecord]


class ToolCatalogEntry(BaseModel):
    name: str
    title: str
    description: str
    grounding_type: str
    input_schema: dict[str, object]


class ToolCatalogResponse(BaseModel):
    tools: list[ToolCatalogEntry]


class ToolInvocationRequest(BaseModel):
    arguments: dict[str, object] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, min_length=1, max_length=255)


class ToolInvocationResponse(BaseModel):
    tool: ToolCall


class HealthResponse(BaseModel):
    status: str
    ready: bool
    document_count: int
    chunk_count: int
    fingerprint: str | None = None
    redis_ready: bool = False
    upload_count: int = 0
    tool_count: int = 0
    startup_error: str | None = None

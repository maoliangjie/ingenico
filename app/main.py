from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from openai import APIError, AuthenticationError, RateLimitError

from app.config import Settings
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ToolCatalogEntry,
    ToolCatalogResponse,
    ToolInvocationRequest,
    ToolInvocationResponse,
    UploadListResponse,
    UploadRecord,
)
from app.services.rag_service import RagService


def create_app(
    rag_service: RagService | Any | None = None,
    initialize_service: bool = True,
) -> FastAPI:
    service = rag_service or RagService(Settings.from_env())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.startup_error = None
        if initialize_service:
            try:
                service.initialize()
            except Exception as exc:
                app.state.startup_error = str(exc)
        app.state.rag_service = service
        yield

    app = FastAPI(
        title="Ingenico Stage-3 Agentic RAG",
        version="3.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_rag_service(request: Request) -> Any:
        return request.app.state.rag_service

    def ensure_ready(request: Request) -> None:
        if request.app.state.startup_error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "RAG service is not ready. Fix the startup error first: "
                    f"{request.app.state.startup_error}"
                ),
            )

    @app.get("/health", response_model=HealthResponse)
    def health_check(request: Request, rag: Any = Depends(get_rag_service)) -> HealthResponse:
        health = rag.health()
        health["startup_error"] = request.app.state.startup_error
        if request.app.state.startup_error:
            health["status"] = "degraded"
            health["ready"] = False
        return HealthResponse(**health)

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request, rag: Any = Depends(get_rag_service)) -> ChatResponse:
        ensure_ready(request)
        result = _run_chat(
            rag=rag,
            message=payload.message,
            session_id=payload.session_id,
            top_k=payload.top_k,
        )
        return ChatResponse(**result)

    @app.post("/chat/stream")
    def stream_chat(
        payload: ChatRequest,
        request: Request,
        rag: Any = Depends(get_rag_service),
    ) -> StreamingResponse:
        def event_stream():
            try:
                ensure_ready(request)
                result = _run_chat(
                    rag=rag,
                    message=payload.message,
                    session_id=payload.session_id,
                    top_k=payload.top_k,
                )
                yield _sse("start", {"session_id": result["session_id"], "cache_hit": result["cache_hit"]})
                yield _sse("tools", {"tool_calls": result["tool_calls"]})
                yield _sse("sources", {"sources": result["sources"]})
                for token in result["answer"].split():
                    yield _sse("token", {"text": token + " "})
                yield _sse(
                    "done",
                    {
                        "session_id": result["session_id"],
                        "answer": result["answer"],
                        "cache_hit": result["cache_hit"],
                        "sources": result["sources"],
                        "tool_calls": result["tool_calls"],
                    },
                )
            except HTTPException as exc:
                yield _sse("error", {"detail": exc.detail, "status_code": exc.status_code})
            except Exception as exc:  # pragma: no cover - defensive SSE fallback
                yield _sse("error", {"detail": str(exc), "status_code": 500})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.get("/uploads", response_model=UploadListResponse)
    def list_uploads(request: Request, rag: Any = Depends(get_rag_service)) -> UploadListResponse:
        ensure_ready(request)
        return UploadListResponse(files=[UploadRecord(**item) for item in rag.list_uploads()])

    @app.get("/mcp/tools", response_model=ToolCatalogResponse)
    def list_tools(request: Request, rag: Any = Depends(get_rag_service)) -> ToolCatalogResponse:
        ensure_ready(request)
        return ToolCatalogResponse(tools=[ToolCatalogEntry(**item) for item in rag.list_tools()])

    @app.post("/mcp/tools/{tool_name}", response_model=ToolInvocationResponse)
    def invoke_tool(
        tool_name: str,
        payload: ToolInvocationRequest,
        request: Request,
        rag: Any = Depends(get_rag_service),
    ) -> ToolInvocationResponse:
        ensure_ready(request)
        try:
            result = rag.invoke_tool(
                tool_name,
                arguments=payload.arguments,
                session_id=payload.session_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return ToolInvocationResponse(tool=result)

    @app.post("/upload", response_model=UploadRecord)
    async def upload_file(
        request: Request,
        file: UploadFile = File(...),
        rag: Any = Depends(get_rag_service),
    ) -> UploadRecord:
        ensure_ready(request)
        content = await file.read()
        try:
            created = rag.create_upload(file.filename or "upload.txt", content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return UploadRecord(**created)

    @app.put("/uploads/{file_id}", response_model=UploadRecord)
    async def replace_upload(
        file_id: str,
        request: Request,
        file: UploadFile = File(...),
        rag: Any = Depends(get_rag_service),
    ) -> UploadRecord:
        ensure_ready(request)
        content = await file.read()
        try:
            updated = rag.replace_upload(file_id, file.filename or "upload.txt", content)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Upload '{file_id}' was not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return UploadRecord(**updated)

    @app.delete("/uploads/{file_id}", status_code=204)
    def delete_upload(file_id: str, request: Request, rag: Any = Depends(get_rag_service)) -> Response:
        ensure_ready(request)
        try:
            rag.delete_upload(file_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Upload '{file_id}' was not found.") from exc
        return Response(status_code=204)

    return app


def _run_chat(rag: Any, message: str, session_id: str | None, top_k: int | None) -> dict[str, Any]:
    try:
        return rag.chat(message=message, session_id=session_id, top_k=top_k)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=f"Upstream model provider rate limited the request: {exc}",
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream model provider rejected credentials: {exc}",
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream model provider error: {exc}",
        ) from exc


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


app = create_app()

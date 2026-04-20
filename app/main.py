from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from openai import APIError, AuthenticationError, RateLimitError

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse, HealthResponse
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
        title="Stage-1 Local RAG MVP",
        version="1.0.0",
        lifespan=lifespan,
    )

    def get_rag_service(request: Request) -> Any:
        return request.app.state.rag_service

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
        if request.app.state.startup_error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "RAG service is not ready. Fix the startup error first: "
                    f"{request.app.state.startup_error}"
                ),
            )
        try:
            result = rag.chat(
                message=payload.message,
                session_id=payload.session_id,
                top_k=payload.top_k,
            )
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
        return ChatResponse(**result)

    return app


app = create_app()

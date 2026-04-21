# Backend API Module

## What it implements
- FastAPI application lifecycle in `app/main.py`
- Health, non-streaming chat, SSE chat, and upload-management endpoints
- Provider error mapping and degraded-startup handling

## What it solves
- Exposes a stable HTTP contract for RAG, uploads, and operational status
- Keeps startup failures visible without crashing the whole service contract
- Provides both compatibility (`POST /chat`) and progressive UX (`POST /chat/stream`)

## Technologies used
- FastAPI
- Starlette streaming responses
- Pydantic request and response models
- OpenAI-compatible error classes for upstream translation

## How it interacts with other modules
- Pulls runtime configuration from `app/config.py`
- Delegates all business logic to `app/services/rag_service.py`
- Serializes service outputs using `app/schemas.py`
- Serves as the HTTP boundary consumed by the frontend, scripts, and Postman assets

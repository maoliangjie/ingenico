# Backend API Module

## What it implements
- FastAPI application lifecycle in `app/main.py`
- Health, non-streaming chat, SSE chat, upload-management endpoints, and MCP-style tool endpoints
- Provider error mapping and degraded-startup handling
- Stage-3 tool catalog and direct tool invocation surfaces

## What it solves
- Exposes a stable HTTP contract for RAG, uploads, and operational status
- Keeps startup failures visible without crashing the whole service contract
- Provides both compatibility (`POST /chat`) and progressive UX (`POST /chat/stream`)
- Gives operators and external clients a structured way to inspect and call runtime tools

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

## Stage-3 API additions
- `GET /mcp/tools`: returns tool descriptors, input schemas, and grounding types.
- `POST /mcp/tools/{tool_name}`: invokes one tool with `arguments` and optional `session_id`.
- `POST /chat`: now returns `tool_calls` alongside `session_id`, `answer`, `sources`, and `cache_hit`.
- `POST /chat/stream`: emits `tools` before token output, then includes `sources` and `tool_calls` in `done`.

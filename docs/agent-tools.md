# Agent Tools Module

## What it implements
- A small stage-3 tool router in `app/services/agent_tools.py`.
- A structured tool catalog exposed through `GET /mcp/tools`.
- Direct tool invocation through `POST /mcp/tools/{tool_name}`.
- Tool execution traces returned from chat as `tool_calls`.

## What it solves
- Makes RAG behavior inspectable instead of hiding every decision inside one prompt.
- Lets operational questions use runtime facts such as health, upload state, and session history.
- Provides an MCP-style boundary that can be expanded later without changing the core chat contract again.

## Technologies used
- Python dataclasses for tool descriptors and execution records.
- Pydantic schemas for HTTP serialization.
- FastAPI routes for catalog and invocation.
- Existing Chroma, Redis, and upload-store services as tool backends.

## How it interacts with other modules
- `RagService.chat()` asks the toolbox to plan and execute tools before generation.
- `search_knowledge` calls the vector store and produces the same `sources` returned to clients.
- `get_system_health` reads `RagService.health()`.
- `list_uploads` reads `UploadStore` records.
- `recall_session_history` uses Redis-backed session history already loaded for the active turn.
- Redis cache keys include tool results so cached answers stay tied to the same grounded facts.

## Current tools
- `search_knowledge`: retrieves relevant snippets from static and uploaded knowledge sources.
- `get_system_health`: reports readiness, Redis state, document counts, chunk counts, and uploads.
- `list_uploads`: lists uploaded knowledge files and timestamps.
- `recall_session_history`: returns recent messages for the active `session_id`.

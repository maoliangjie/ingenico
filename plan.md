# Ingenico Roadmap

## Stage 1
Status: completed

Delivered:
- Local document RAG over `data/`
- FastAPI `GET /health` and `POST /chat`
- Chroma vector store with manifest-based rebuilds
- Local BGE embeddings and OpenAI-compatible chat
- Dockerized backend startup

## Stage 2
Status: completed

Delivered:
- Redis-backed session memory and LLM response cache
- SSE streaming endpoint at `POST /chat/stream`
- Upload lifecycle APIs: create, list, replace, delete
- Local upload persistence under `storage/uploads/`
- Shared retrieval across static `data/` and uploaded files
- React + TypeScript frontend in `frontend/`
- Module docs in `docs/`
- Verification scripts in `scripts/verify/`
- Postman collection and environment in `postman/`

Implementation notes:
- Stage 2 replaced the old SQLite-first runtime path instead of keeping dual memory stacks.
- Index refresh prefers manifest checks and falls back to controlled full rebuilds after upload changes.
- Client-visible answers always strip `<think>` content while backend logs retain it.

## Stage 3
Status: completed

Delivered:
- Agent tool router integrated into `POST /chat` and `POST /chat/stream`
- Structured tool traces returned as `tool_calls`
- MCP-style tool catalog at `GET /mcp/tools`
- Direct tool invocation at `POST /mcp/tools/{tool_name}`
- Runtime tools for knowledge search, system health, upload listing, and session recall
- Frontend tool trace panel for each answer
- Test coverage and verification script for the stage-3 tool layer

Implementation notes:
- The default chat path always routes through `search_knowledge` before generation.
- Operational questions can also call health, upload, or session-history tools.
- Tool results are included in cache keys and prompt grounding so cached answers match the same runtime facts.
- Client-visible answers still strip `<think>` content; tool traces expose structured facts, not hidden reasoning.

## Stage 4
Status: planned

Candidate scope:
- Voice input and output
- Realtime transport upgrades
- Broader operational hardening

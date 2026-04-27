# AGENTS.md

## Project Goal
- Build a stage-3 local-document RAG product with FastAPI, LangChain, Chroma, Redis memory/cache, OpenAI-compatible chat, local BGE embeddings, upload management, a React + TypeScript frontend, Docker Compose, and an MCP-style agent tool layer.

## Repository Map
- `app/`: API entrypoint, config, schemas, and orchestration services.
- `app/services/`: retrieval, Redis store, upload persistence, document loading, and agent tool routing.
- `frontend/`: Vite React + TypeScript operator console.
- `data/`: static knowledge inputs (`.txt`, `.md`, `.json`, `.pdf` only).
- `models/`: local embedding model files for offline startup.
- `storage/`: runtime artifacts for Chroma, upload metadata, and temporary files.
- `docs/`: module documentation and operating notes.
- `scripts/verify/`: CLI verification scripts for API, uploads, SSE, cache, and agent tools.
- `postman/`: collection and environment assets for manual API checks.
- `tests/`: automated regression coverage.
- `plan.md`: staged roadmap; keep it aligned with the implemented state.

## Runbook
- Copy `.env.example` to `.env` and set chat-provider credentials.
- Start the backend locally with `uvicorn app.main:app --reload`.
- Start the full stack with `docker compose up --build`.
- If Docker cannot pull `python:3.13-slim`, tag the local API image and rebuild with `API_BASE_IMAGE=ingenico-api-base:local`.
- Start the frontend locally with `cd frontend && npm install && npm run dev`.
- Use `GET /health` to verify readiness.
- Use `POST /chat` for non-streaming answers and `POST /chat/stream` for SSE.
- Use `GET /mcp/tools` and `POST /mcp/tools/{tool_name}` to inspect or invoke stage-3 tools directly.
- Use the upload endpoints or the frontend uploads panel to manage dynamic knowledge files.

## API Contract
- `GET /health`: readiness, index stats, Redis state, upload count, tool count, startup error.
- `POST /chat`: `message`, optional `session_id`, optional `top_k`; returns `session_id`, `answer`, `sources`, `cache_hit`, `tool_calls`.
- `POST /chat/stream`: same request body as `/chat`; emits `start`, `tools`, `sources`, `token`, `done`, `error`.
- `POST /upload`: multipart file upload for `.txt`, `.md`, `.json`, `.pdf`.
- `GET /uploads`: list uploaded files and metadata.
- `PUT /uploads/{file_id}`: replace an uploaded file.
- `DELETE /uploads/{file_id}`: remove an uploaded file.
- `GET /mcp/tools`: list MCP-style tool descriptors and input schemas.
- `POST /mcp/tools/{tool_name}`: invoke a tool with structured arguments and optional `session_id`.

## Global Rules
- Answers must stay grounded in retrieved context; prefer explicit uncertainty over guessing.
- Remove `<think>` or similar reasoning tags from all client-visible responses, and log the redundant, procedural information to the backend.
- Log stripped reasoning server-side for debugging.
- Redis is the primary store for session memory and LLM cache in stage 3.
- Rebuild the vector index when source content or embedding configuration changes.
- Uploaded files persist under `storage/uploads/` and count as first-class knowledge sources.
- Supported ingestion types remain limited to `.txt`, `.md`, `.json`, and `.pdf`.
- JSON ingestion must flatten nested keys into readable text lines.
- Return source snippets with every answer for RAG verification.
- Keep provider config separate for chat and embeddings.
- Route operational questions through structured tools before generation when that yields more reliable answers.
- Keep the MCP-style tool catalog aligned with the actual tool router and response payloads.

## Environment Defaults
- Default chat API base: `https://api.minimaxi.com/v1`.
- Default chat model: `MiniMax-M2.1`.
- Default embedding provider: `local`.
- Default local embedding model: `models/bge-small-zh-v1.5`.
- Default Redis URL: `redis://localhost:6379/0`.
- Default retrieval count: `4`.
- Default history window: `6` messages.

## Implementation Constraints
- Remove outdated files from the project in a timely manner as the codebase evolves, and keep track of such changes using docs/md.
- Do not add unsupported upload types or object storage in stage 3.
- Keep runtime state under `storage/` and keep secrets out of git.
- Keep this file under 100 lines.

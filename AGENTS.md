# AGENTS.md

## Project Goal
- Build a stage-1 local-document RAG MVP with FastAPI, LangChain, Chroma, OpenAI-compatible chat, local BGE embeddings, SQLite memory, and Docker Compose.

## Repository Map
- `app/`: API, config, RAG orchestration, document loading, memory storage.
- `data/`: local knowledge base inputs (`.txt`, `.md`, `.json` only).
- `models/`: local embedding model files for offline startup.
- `storage/`: runtime artifacts for Chroma and SQLite; never commit secrets here.
- `tests/`: unit and API tests.
- `plan.md`: roadmap across stages; do not duplicate it here.

## Runbook
- Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
- Start locally with `uvicorn app.main:app --reload`.
- Start with Docker using `docker compose up --build`.
- Use `GET /health` to verify readiness.
- Use `POST /chat` for question answering.

## API Contract
- `POST /chat` request: `message`, optional `session_id`, optional `top_k`.
- `POST /chat` response: `session_id`, `answer`, `sources`.
- `GET /health` returns service readiness and index stats.

## Global Rules
- Stage 1 supports only local file ingestion; do not add upload APIs yet.
- Keep answers grounded in retrieved context; prefer explicit uncertainty over guessing.
- Persist conversation history in SQLite by `session_id`.
- Rebuild the vector index only when the source data fingerprint changes.
- Keep the implementation backend-only; no frontend work in this stage.
- Keep sample knowledge files small and readable so the repo stays easy to inspect.
- Favor clear, testable functions over large chains with hidden behavior.

## Environment Defaults
- Default API base: `https://openrouter.ai/api/v1`.
- Default chat model: `google/gemma-4-26b-a4b-it:free`.
- Default embedding provider: `local`.
- Default local embedding model: `models/bge-small-zh-v1.5`.
- Default retrieval count: `4`.
- Default history window: `6` messages.

## Implementation Constraints
- Supported loaders: `.txt`, `.md`, `.json`.
- JSON ingestion should flatten nested keys into readable text lines.
- Return source snippets with each answer for RAG verification.
- Store runtime state under `storage/`.
- Keep chat provider config separate from embedding provider config.
- Keep this file under 100 lines.

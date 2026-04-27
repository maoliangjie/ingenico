# Memory and Cache Module

## What it implements
- Redis-backed conversation history keyed by `session_id`
- Redis-backed answer cache keyed by model, question, history, retrieved sources, tool results, and `top_k`
- Health visibility for Redis connectivity

## What it solves
- Replaces the old SQLite-only runtime path with a faster shared in-memory store
- Preserves multi-turn context across requests and service restarts
- Reduces duplicate model calls for identical grounded prompts and identical tool facts

## Technologies used
- Redis via `redis-py`
- JSON payload storage for messages and cache entries
- `fakeredis` for test coverage without a real Redis daemon

## How it interacts with other modules
- `app/services/redis_store.py` encapsulates Redis reads, writes, and cache keys
- `app/services/rag_service.py` uses Redis for both history and answer caching
- `app/services/agent_tools.py` can use recent history as a structured tool result
- `GET /health` exposes Redis readiness through the API layer
- Verification scripts use the additive `cache_hit` response field to prove cache behavior

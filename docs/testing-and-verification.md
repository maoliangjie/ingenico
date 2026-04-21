# Testing and Verification Module

## What it implements
- Automated pytest coverage for API, retrieval, Redis store, upload store, and RAG helpers
- Command-line verification scripts under `scripts/verify/`
- Postman collection and environment under `postman/`

## What it solves
- Gives both automated and manual ways to validate the stage-2 stack
- Covers the new Redis, SSE, and upload capabilities introduced in this stage
- Provides repeatable entry points for reviewers who prefer scripts or GUI tooling

## Technologies used
- Pytest
- Python standard library HTTP utilities for verification scripts
- Postman Collection v2.1 JSON

## How it interacts with other modules
- Automated tests import `app.main`, `app.services.*`, and schema models directly
- Verification scripts call the live FastAPI endpoints
- Postman assets mirror the same API surface used by the frontend
- Health, cache, upload, and stream checks all depend on the backend and Redis stack being up

## Verification Commands
- Backend tests: `python -m pytest -q`
- Frontend build check: `cd frontend && npm install && npm run build`
- Full stack: `docker compose up --build`
- Health script: `python scripts/verify/health_check.py`
- Non-stream chat: `python scripts/verify/chat_once.py --message "How do I start a new conversation?"`
- Stream chat: `python scripts/verify/chat_stream.py --message "How do I start a new conversation?"`
- Upload lifecycle: `python scripts/verify/upload_lifecycle.py`
- Cache check: `python scripts/verify/redis_cache_check.py --message "How do I start a new conversation?"`

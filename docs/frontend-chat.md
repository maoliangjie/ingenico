# Frontend Chat Module

## What it implements
- A Vite React + TypeScript single-page console in `frontend/`
- Streaming answer display, source rendering, session reuse, and upload controls
- Health/status visibility for operators

## What it solves
- Provides a minimal product surface instead of raw API-only testing
- Makes SSE answers and retrieval evidence visible in one place
- Lets operators curate uploaded knowledge without leaving the app

## Technologies used
- React 18
- TypeScript
- Vite
- Native Fetch streaming for SSE parsing
- Hand-authored CSS with a restrained control-room layout

## How it interacts with other modules
- Calls `GET /health`, `POST /chat/stream`, and the upload APIs through `frontend/src/api.ts`
- Renders sources returned by the backend without additional transformation
- Uses the backend session contract by storing and replaying `session_id`
- Depends on CORS settings in `app/main.py` for local development

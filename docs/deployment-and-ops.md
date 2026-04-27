# Deployment and Operations Module

## What it implements
- Docker image for the API service
- Docker Compose stack for Redis, API, and frontend
- Environment-driven runtime configuration
- Local base-image override for machines that cannot pull `python:3.13-slim`

## What it solves
- Makes the stack reproducible for local development and review
- Gives the API a stable Redis target inside containers
- Keeps runtime artifacts mounted and inspectable on the host machine

## Technologies used
- Docker
- Docker Compose
- `.env` / `.env.example` configuration
- Health checks against `GET /health`

## How it interacts with other modules
- `Dockerfile` builds the FastAPI service with app code and dependencies
- `docker-compose.yml` wires Redis, API, and frontend together
- `app/config.py` reads the environment variables exposed by compose or local shells
- `docs/testing-and-verification.md` references the same startup paths for validation

## Local image fallback
If Docker Desktop cannot pull `python:3.13-slim`, rebuild from the existing local API image:

```powershell
docker tag ingenico-api:latest ingenico-api-base:local
$env:API_BASE_IMAGE='ingenico-api-base:local'
docker compose build api
docker compose up -d redis api frontend
```

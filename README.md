# Chatico Ads

Dockerized FastAPI + Vue 3 analytics workspace for Meta, Google Ads, and TikTok Ads reporting, JWT auth, OAuth account connection, and AI proxy workflows.

## Stack

- Backend: FastAPI, SQLAlchemy Async, PostgreSQL, Alembic
- Frontend: Vue 3 + TypeScript + Vite
- Infra: Docker Compose, Nginx
- AI proxy: Anthropic, OpenAI, Gemini via backend-only calls

## Quick Start

```bash
cp .env.example .env
cd docker
docker compose --env-file ../.env up -d --build
```

- Frontend: `http://localhost:4173`
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health/live`

## Local Checks

```bash
poetry run pytest
docker run --rm -u $(id -u):$(id -g) -v "$PWD":/workspace -w /workspace/front node:22-alpine sh -lc 'npm install && npm run build'
```

## Project Layout

- `src/` — FastAPI app, use cases, services, repositories, security
- `database/` — Alembic config and migrations
- `front/` — Vue SPA with auth, Meta onboarding, dashboard, and AI rail
- `docker/` — API/frontend images and compose stack
- `tests/` — integration and unit coverage

## Notes

- Fill real Meta and AI credentials in `.env` before using OAuth, reporting, or AI verdicts against production accounts.
- `meta-ads-report.html` is kept in the repository as the source dashboard reference.

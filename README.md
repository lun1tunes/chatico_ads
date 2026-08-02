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

## AI Prompt Architecture

- Prompt files live in `prompts/` and are loaded at request time in UTF-8, so text changes apply without changing backend business logic.
- Active prompt files:
  - `prompts/01_report_content.txt`
  - `prompts/02_shared_ai_philosophy.txt`
  - `prompts/03_chat_prompt.txt`
  - `prompts/04_auto_verdict_prompt.txt`
  - `prompts/05_integration_scheme.md`
- Chat assembly order:
  1. `02_shared_ai_philosophy.txt`
  2. `03_chat_prompt.txt`
  3. `01_report_content.txt` with the current `report_context`
  4. the latest user question
- Auto Verdict assembly order:
  1. `02_shared_ai_philosophy.txt`
  2. `04_auto_verdict_prompt.txt`
  3. `01_report_content.txt` with the current `report_context`
- Prompt template variables:
  - Shared AI Philosophy: `{domain_refusal_text}`
  - Chat Prompt: `{language}`
  - Auto Verdict Prompt: `{normalized_language}`, `{language_name}`, `{scope_focus}`
- Runtime payload fields injected by the prompt service:
  - Chat: current `report_context` plus the latest `user_message`
  - Auto Verdict: current `report_context`
- Prompt loading and validation live in `src/core/services/ai_prompt_service.py`.
- API routes log request type, ad account identifier, report period, and prompt file checksums. API keys are never logged.
- Old inline Chat and Auto Verdict system prompts were removed from the request assembly path. Routes now use the prompt service only.

## AI Change Checklist

- `prompts/` is the single runtime source for Chat and Auto Verdict prompt text.
- Shared AI Philosophy is injected into both Chat and Auto Verdict.
- `report_context` still comes from the real dashboard report builders in `src/core/utils/ai_context.py`.
- Out-of-domain and specialist-evaluation guardrails now live in prompt configuration instead of hardcoded route prompts.
- Missing prompt variables and empty `report_context` raise a controlled `503` API error and emit diagnostic logs.
- Added unit coverage for prompt bundle assembly and prompt configuration failures.
- Added route coverage for prompt-configuration failures and updated AI route tests for the new bundle contract.

## AI Acceptance Checklist

Validated on `2026-08-02` with:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.13-slim sh -lc 'python -m pip install -q poetry && poetry config virtualenvs.create false && poetry install --with dev --no-interaction --no-ansi >/tmp/poetry-install.log && pytest --no-cov -q tests/integration/test_api_routes.py tests/integration/test_auth_api.py tests/unit/test_ai_prompt_service.py tests/unit/test_auto_verdict_fallback.py tests/unit/test_google_ads_use_cases.py tests/unit/test_meta_graph_api.py'
```

- Campaign comparison uses live `report_context` payloads and the shared prompt bundle contract, covered in `tests/integration/test_api_routes.py` and `tests/unit/test_ai_prompt_service.py`.
- Specialist and agency questions are constrained by the shared philosophy plus the dedicated chat special-case block, asserted in `tests/unit/test_ai_prompt_service.py`.
- Out-of-domain requests and prompt-injection attempts are constrained by the exact Domain Policy refusal text and the "do not continue" rule in `prompts/02_shared_ai_philosophy.txt`.
- No-active-campaign verdicts are forced through a guardrail fallback that explicitly says delivery was inactive, covered in `tests/integration/test_api_routes.py` and `tests/unit/test_auto_verdict_fallback.py`.
- Insufficient-data cases fall back to explicit "not enough data" wording in `src/core/utils/auto_verdict_fallback.py`.
- Legacy inline AI system prompts are removed from the active request path: AI routes assemble prompts only through `src/core/services/ai_prompt_service.py`, and request logging records prompt checksums instead of prompt bodies or API keys.

# HANDOFF_AGENT

Этот файл нужен следующему инженеру или coding agent, который будет продолжать проект на другом VPS.

Сначала прочитай [AGENTS.md](./AGENTS.md) как основной набор правил по репозиторию. После этого используй этот документ как рабочий handoff по реальному состоянию проекта, деплою и operational-нюансам.

## 1. Актуальная реальность проекта

- Путь к репозиторию на исходном VPS: `/home/lun1z/chatico_ads`
- Текущая ветка: `main`
- Текущий `HEAD` на момент handoff: `783ba28`
- Последний commit в `HEAD`: `Implement Google Ads report generation and disconnection features. Added API endpoints for generating Google Ads reports and disconnecting Google Ads connections. Enhanced frontend components to support Google Ads disconnection flow, including user confirmation and success notifications. Updated tests to cover new functionalities and ensure proper integration with existing features.`
- Фактический backend stack: FastAPI, SQLAlchemy async, PostgreSQL, Alembic, dependency-injector
- Фактический frontend stack: Vue 3, TypeScript, Vite, статический Nginx-контейнер
- Фактическая infra: Docker Compose с сервисами `api`, `front`, `postgres`
- В текущем коде нет Redis, Celery, worker/beat контейнеров
- Google Ads теперь реализован не только на уровне OAuth: в коде есть сохранение credentials, синхронизация customer tree, dashboard-отчёты, AI summary/chat и disconnect flow

Важное расхождение:

- `AGENTS.md` описывает референсную инженерную модель и до сих пор упоминает Python 3.11 и Redis/Celery-подобную инфраструктуру.
- Источник правды по текущему runtime находится в `pyproject.toml`, Dockerfile и compose-файлах:
  - runtime Python здесь `3.13`
  - в compose только `postgres`, `api`, `front`
- Если `AGENTS.md` и исполняемый код расходятся, для runtime доверяй коду, а для инженерной дисциплины и стилевых ограничений доверяй `AGENTS.md`.

## 2. Проверенное состояние перед handoff

Проверка backend на исходном VPS:

- `poetry run pytest -q` прошёл
- Результат: `66 passed in 5.37s`
- Покрытие: `87.53%`

Проверка frontend на исходном VPS:

- На хосте нет `npm`
- Docker установлен и рабочий: `Docker version 26.1.5+dfsg1`
- `npm ci` повторно проверен в чистом `node:22-bookworm` контейнере и сейчас падает, потому что `front/package-lock.json` не синхронизирован с `front/package.json`
- Из-за отсутствия host-level `npm` и дрейфа lockfile я не переисполнял frontend `npm test` и `npm run build` именно для текущей ревизии Google Ads UI на этом VPS

Вывод:

- Backend состояние подтверждено тестами прямо на этом VPS
- Google Ads backend flow подтверждён кодом и backend-интеграционными тестами
- Для frontend остаётся технический долг: нормализовать lockfile и отдельно прогнать UI smoke/build уже на чистой Node-среде

## 3. Состояние рабочего дерева

На момент проверки перед обновлением этого handoff `git status --short` был пустым.

Что это значит practically:

- приложение воспроизводится обычным `git clone` + checkout текущего `HEAD`
- больше нет отдельного незакоммиченного product diff, который надо вручную переносить на другой VPS
- если этот `HANDOFF_AGENT.md` не будет закоммичен отдельно после моей правки, единственное локальное отличие будет именно в нём

Итог:

- для переноса нового VPS больше не нужен отдельный patch с Google Ads функциональностью
- источник правды по текущему продукту теперь уже находится в git history, а не в грязном worktree

## 4. Карта проекта

- `src/main.py`: bootstrap FastAPI, CORS, `/health/live`, `/health/ready`
- `src/api_v1/auth/views.py`: register, login, refresh, logout, `/me`, обновление locale
- `src/api_v1/meta/views.py`: Meta OAuth start/callback, ad accounts, disconnect, data deletion callback/status
- `src/api_v1/google_ads/views.py`: Google Ads OAuth start/callback, customer sync, disconnect
- `src/api_v1/dashboard/views.py`: endpoints Meta Ads и Google Ads dashboard-отчётов
- `src/api_v1/ai/views.py`: каталог провайдеров, сохранённые user provider keys, auto verdict и chat по Meta/Google Ads dashboard context
- `src/core/config.py`: валидируемый env-контракт
- `src/core/security/encryption_service.py`: Fernet-шифрование для сохранённых credentials
- `src/core/infrastructure/google_ads_api.py`: OAuth token exchange/refresh, customer discovery, Google Ads reporting queries
- `src/core/services/google_ads_report_service.py`: нормализация Google Ads отчёта в общий dashboard shape и short-lived in-memory cache
- `src/core/use_cases/google_ads.py`: OAuth callback orchestration, sync customers, disconnect
- `src/core/use_cases/dashboard.py`: orchestration Meta/Google Ads report generation
- `front/src/App.vue`: единый UI для Meta/Google Ads аккаунтов, AI analysis и provider-aware chat/settings
- `front/src/App.test.ts`: smoke/behavior tests фронтового state flow
- `database/migrations/versions/`: Alembic migrations
- `docker/docker-compose.yml`: runtime stack
- `docker/Dockerfile`: backend image, также запускает Alembic при старте
- `docker/Dockerfile.front`: frontend build image с Vite build args
- `nginx.conf.example`: host Nginx snippet для subpath-деплоя под `/chatico_ads/`

## 5. Runtime-поведение, которое нужно понимать

### Auth

- Access token возвращается в JSON.
- Refresh token хранится в `HttpOnly` cookie.
- Имя refresh cookie по умолчанию: `chatico_ads_refresh_token`.
- Путь cookie вычисляется из `FRONTEND_URL`, если `REFRESH_COOKIE_PATH` пустой.
- Это важно для subpath-деплоя. Если `FRONTEND_URL=https://example.com/chatico_ads`, путь cookie станет `/chatico_ads`.

### Meta

- OAuth callback endpoint: `/api/v1/meta/oauth/callback`
- После callback backend редиректит во frontend по схеме: `FRONTEND_URL + /connections?...`
- Endpoint списка ad accounts: `/api/v1/meta/ad-accounts`
- Endpoint отчёта: `/api/v1/dashboard/meta/ad-accounts/{ad_account_id}/report`
- Endpoint disconnect: `DELETE /api/v1/meta/connections`
- Endpoint data deletion callback: `POST /api/v1/meta/data-deletion/callback`
- Endpoint статуса data deletion: `GET /api/v1/meta/data-deletion/status/{confirmation_code}`

### Google Ads

- OAuth start endpoint: `/api/v1/google-ads/oauth/start`
- OAuth callback endpoint: `/api/v1/google-ads/oauth/callback`
- Endpoint списка customers: `/api/v1/google-ads/customers`
- Endpoint отчёта: `/api/v1/dashboard/google-ads/customers/{customer_id}/report`
- Endpoint disconnect: `DELETE /api/v1/google-ads/connections`
- Google Ads здесь уже не connection-only: callback сохраняет encrypted credentials, синхронизирует customers в базе и потом эти данные используются для dashboard/AI flow
- Кэш Google Ads отчёта сейчас только in-memory с коротким TTL. DB snapshot слоя, как у Meta, здесь пока нет.
- Если конфиг неполный, старт OAuth вернёт `503`.

### AI

- Внутренний AI provider работает только серверно и используется для auto verdict и fallback chat-сценариев.
- Поддерживаемые внутренние провайдеры в текущем коде: `gemini` и `anthropic`
- Пользовательские provider keys сохраняются в базе в зашифрованном виде.
- Auto verdict endpoints:
  - `POST /api/v1/ai/meta/ad-accounts/{ad_account_id}/auto-verdict`
  - `POST /api/v1/ai/google-ads/customers/{customer_id}/auto-verdict`
- Chat endpoints:
  - `POST /api/v1/ai/meta/ad-accounts/{ad_account_id}/chat`
  - `POST /api/v1/ai/google-ads/customers/{customer_id}/chat`
- Если поменять `FIELD_ENCRYPTION_KEY` после того, как данные уже появились, сохранённые user AI keys и OAuth tokens перестанут расшифровываться.

## 6. Env-контракт

Бери `.env.example` как стартовую точку. Приложение достаточно жёстко валидирует конфиг в `src/core/config.py`.

По факту обязательны:

- `JWT_SECRET_KEY`
- `FIELD_ENCRYPTION_KEY`
- `META_APP_ID`
- `META_APP_SECRET`
- `META_OAUTH_REDIRECT_URI`
- `FRONTEND_URL`
- `PUBLIC_APP_URL`
- Хотя бы один внутренний AI key должен быть непустым на старте:
  - `INTERNAL_GEMINI_API_KEY`
  - или `INTERNAL_ANTHROPIC_API_KEY`

Что здесь реально важно:

- `DATABASE_URL` внутри Docker Compose должен использовать hostname `postgres`, а не `localhost`
- `PUBLIC_APP_URL` используется для сборки Meta data deletion status URL
- `CORS_ALLOWED_ORIGINS` должен содержать origin без path
- `VITE_*` переменные являются build-time переменными, а не runtime
- Любое изменение `VITE_API_BASE_URL` или `VITE_APP_BASE_PATH` требует пересборки фронта

Генерация секретов:

```bash
python3 - <<'PY'
import base64
import os
import secrets

print("JWT_SECRET_KEY=" + secrets.token_urlsafe(64))
print("FIELD_ENCRYPTION_KEY=" + base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
```

Правила непрерывности секретов при переносе существующей базы:

- Сохрани тот же `FIELD_ENCRYPTION_KEY`, иначе сломаются сохранённые Meta tokens, Google tokens и user AI keys
- Сохрани тот же `JWT_SECRET_KEY`, если хочешь, чтобы существующие refresh/access tokens оставались валидными
- Если один из этих секретов меняется намеренно, заранее считай пользовательские последствия

## 7. Рекомендуемые env-профили

### Вариант A: отдельный домен или поддомен

Используй это, если приложение живёт на отдельном хосте, например `https://ads.example.com`.

```env
FRONTEND_URL=https://ads.example.com
PUBLIC_APP_URL=https://ads.example.com
VITE_APP_BASE_PATH=/
VITE_API_BASE_URL=/api/v1
CORS_ALLOWED_ORIGINS=https://ads.example.com
META_OAUTH_REDIRECT_URI=https://ads.example.com/api/v1/meta/oauth/callback
GOOGLE_OAUTH_REDIRECT_URI=https://ads.example.com/api/v1/google-ads/oauth/callback
REFRESH_COOKIE_SECURE=true
REFRESH_COOKIE_SAMESITE=lax
```

### Вариант B: subpath под существующим сайтом

Используй это, если приложение живёт под путём вида `https://example.com/chatico_ads`.

```env
FRONTEND_URL=https://example.com/chatico_ads
PUBLIC_APP_URL=https://example.com/chatico_ads
VITE_APP_BASE_PATH=/chatico_ads/
VITE_API_BASE_URL=/chatico_ads/api/v1
CORS_ALLOWED_ORIGINS=https://example.com
META_OAUTH_REDIRECT_URI=https://example.com/chatico_ads/api/v1/meta/oauth/callback
GOOGLE_OAUTH_REDIRECT_URI=https://example.com/chatico_ads/api/v1/google-ads/oauth/callback
REFRESH_COOKIE_SECURE=true
REFRESH_COOKIE_SAMESITE=lax
```

Если используешь subpath-режим:

- `nginx.conf.example` здесь основной reference
- `REFRESH_COOKIE_PATH` лучше оставить пустым, если нет отдельной причины его задавать
- Код сам выведет `/chatico_ads` из `FRONTEND_URL`

## 8. Рецепт деплоя на новый VPS

Рекомендуемая раскладка:

- путь к репозиторию: `/opt/chatico_ads`
- рабочий env-файл: `/opt/chatico_ads/.env`

Базовые требования к серверу:

- Linux VPS с Docker Engine и Docker Compose plugin
- Git
- Опционально для host-level проверки и dev-задач:
  - Python 3.13
  - Poetry

Первичный bootstrap:

```bash
cd /opt
git clone <your-repo-url> chatico_ads
cd chatico_ads
cp .env.example .env
```

Дальше:

1. Забери текущий `HEAD` или нужную ветку как базу; отдельный перенос product patch больше не нужен.
2. Заполни `.env` реальными секретами и публичными URL.
3. Деплой делай из каталога `docker/`.

Запуск или пересборка стека:

```bash
cd /opt/chatico_ads/docker
docker compose --env-file ../.env up -d --build
```

Важный факт про деплой:

- Команда backend-контейнера сама запускает `alembic upgrade head` перед стартом Uvicorn.
- Это удобно, но плохая миграция полностью блокирует старт приложения.
- Перед деплоем на живой системе делай backup базы.

## 9. Reverse proxy и публикация наружу

### Минимальный режим

- Оставить compose как есть
- Ходить во frontend на `:${FRONTEND_PORT}`
- Ходить в API на `:${PORT}`

Для внутреннего тестирования это нормально, но для production я бы так не публиковал.

### Рекомендуемый режим

- Ставить host Nginx перед приложением
- Завершать TLS на host Nginx
- Проксировать во frontend и API порты compose
- Ограничить backend/frontend порты firewall-ом или loopback-only биндингом

Текущий security-нюанс compose:

- Postgres уже привязан только к loopback: `127.0.0.1:${POSTGRES_PORT}:5432`
- API сейчас опубликован как `${PORT}:8000`
- Frontend сейчас опубликован как `${FRONTEND_PORT}:80`

Если новый VPS будет работать через host Nginx, то лучше сделать одно из двух:

1. Закрыть эти порты через firewall.
2. Поменять compose port mapping на loopback-only.

Для subpath-деплоя используй `nginx.conf.example` как основной источник правды.

## 10. Health checks и smoke tests

Базовые команды:

```bash
cd /opt/chatico_ads/docker
docker compose ps
docker compose logs -f api
docker compose logs -f front
docker compose logs -f postgres
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
curl -I http://127.0.0.1:4173/
```

Smoke test auth:

```bash
curl -i -c cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"StrongPass123!","locale":"ru"}' \
  http://127.0.0.1:8000/api/v1/auth/register

curl -i -b cookies.txt \
  http://127.0.0.1:8000/api/v1/auth/me
```

Что считать успехом:

- `/health/live` возвращает `{"status":"ok"}`
- `/health/ready` возвращает `{"status":"ok"}`
- Frontend отвечает `200`
- Register/login возвращает access token и выставляет refresh cookie

## 11. Операции с базой

Именованный volume:

- `chatico_ads_postgres_data`

Разовый backup:

```bash
cd /opt/chatico_ads/docker
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > /root/chatico_ads_$(date +%F_%H%M%S).sql
```

Разовый restore:

```bash
cd /opt/chatico_ads/docker
cat /root/chatico_ads_restore.sql | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

Вход в SQL shell:

```bash
cd /opt/chatico_ads/docker
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 12. Отдельно про frontend build

Это важно зафиксировать отдельно:

- Конфиг frontend baked-in на этапе сборки через `docker/Dockerfile.front`
- `VITE_API_BASE_URL` и `VITE_APP_BASE_PATH` передаются как build args
- Если эти значения меняются, image фронта надо пересобрать

Надёжная команда на пересборку фронта:

```bash
cd /opt/chatico_ads/docker
docker compose --env-file ../.env up -d --build front
```

Текущий caveat с lockfile:

- `front/package-lock.json` сейчас не до конца синхронизирован с `front/package.json`
- На чистой машине `npm ci` сейчас падает
- Пока lockfile не нормализован, нельзя рассчитывать на детерминированный frontend bootstrap на чистой машине
- Я бы сначала пересобрал lockfile через контролируемый `npm install`, затем прогнал `npm test` и `npm run build`, и только после этого закоммитил обновлённый lockfile

## 13. OAuth и compliance checklist

### Meta

- Установить корректный app ID и app secret
- Зарегистрировать точный OAuth redirect URI из `.env`
- Если используется embedded setup или специальная конфигурация, задать `META_OAUTH_CONFIG_ID`
- Зарегистрировать data deletion callback endpoint:
  - `https://<public-base>/api/v1/meta/data-deletion/callback`
  - или `https://<public-base>/chatico_ads/api/v1/meta/data-deletion/callback` для subpath-режима
- Убедиться, что `PUBLIC_APP_URL` совпадает с этим публичным base, потому что status URL строятся именно из него

### Google Ads

- Установить developer token
- Установить OAuth client ID и secret
- Зарегистрировать точный callback URI из `.env`
- Если конфиг заполнен частично, сценарий подключения Google Ads не стартанёт
- OAuth callback сохраняет encrypted access/refresh token pair и пересобирает customer tree пользователя в базе
- Dashboard, AI analysis и AI chat потом работают поверх уже синхронизированных customers и сохранённых credentials
- `DELETE /api/v1/google-ads/connections` удаляет сохранённое Google Ads подключение и связанные customers пользователя

## 14. Острые углы и реальные риски

- Product worktree уже чистый, но сам handoff после редактирования нужно либо закоммитить, либо осознанно оставить локальным.
- Frontend lockfile сейчас не готов для чистого `npm ci`.
- Последняя ревизия Google Ads UI не была заново прогнана через `npm test` и `npm run build` на этом VPS, потому что на хосте нет `npm`, а `npm ci` в чистом Node-контейнере падает из-за lockfile drift.
- Google Ads report cache сейчас только in-memory. После рестарта контейнера или в multi-instance схеме отчёты будут перезапрашиваться, потому что DB snapshot слоя для Google Ads пока нет.
- Ротация `FIELD_ENCRYPTION_KEY` разрушительна для сохранённых credentials, если не делать re-encryption.
- Ротация `JWT_SECRET_KEY` инвалидирует текущие сессии.
- Backend сам запускает Alembic на старте контейнера, поэтому ошибки миграций всплывают прямо при boot.
- Placeholder AI keys могут позволить приложению стартовать, но AI-функции по факту останутся нерабочими.
- Неправильный `PUBLIC_APP_URL` ломает Meta data deletion status URL, даже если основное приложение выглядит здоровым.
- Неправильный `FRONTEND_URL` или неверное поведение cookie path ломают refresh/login в subpath-деплое.

## 15. Что я бы сделал первым делом на втором VPS

1. Забрал бы текущий `HEAD` как базу и отдельно закоммитил бы этот обновлённый handoff, если он нужен в истории.
2. Подготовил бы финальный production `.env` под реальную схему публичного URL.
3. Сразу бы решил, живёт приложение на отдельном домене или под `/chatico_ads/`.
4. Развернул бы стек через Docker Compose и проверил оба health endpoint.
5. Проверил бы register/login/refresh cookie через реальный публичный URL, а не только через localhost.
6. Проверил бы Meta OAuth callback и data deletion callback URL до любого живого пользовательского трафика.
7. Проверил бы руками полный Google Ads flow: OAuth start/callback, список customers, dashboard report, AI analysis/chat и disconnect.
8. Рано нормализовал бы и закоммитил frontend lockfile, чтобы дальше `npm ci` и CI были детерминированными.

## 16. Короткая итоговая оценка

Проект уже в достаточно хорошем состоянии для переноса на другой VPS:

- backend тесты зелёные
- покрытие выше порога
- compose-стек простой
- миграции на месте
- OAuth routes и health checks реализованы
- Google Ads flow уже включает OAuth, customer sync, dashboard report, AI summary/chat и disconnect

Основные operational-риски здесь не архитектурные. Они такие:

- дрейф frontend lockfile
- отсутствие повторной локальной frontend-проверки для последней Google Ads UI ревизии
- неправильная настройка публичного URL или cookie path при деплое
- несохранённая непрерывность секретов при переносе живой базы

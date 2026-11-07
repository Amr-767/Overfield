# AgroSpace Quest

Explainable crop-rotation decision support using NASA Earth data.

## Prerequisites

- Docker Desktop running with Linux containers enabled
- Docker Compose v2 or newer (`docker compose version`)
- Python 3.12+ (Phase 1B verified with Python 3.14 on Windows)
- Node.js 20+ and npm (Phase 1C verified with Node 24 / npm 11)

## Local infrastructure (Phase 1A)

PostgreSQL with PostGIS and Redis run in Docker. Application services are not
defined in Compose; Django runs on the host against the published ports.

### Start infrastructure

1. Copy `.env.example` to `.env` if it is not already present, and set unique
   local-development passwords and a `DJANGO_SECRET_KEY`. Never commit `.env`.
2. Start the services from the repository root:

   ```powershell
   docker compose --env-file .env -f infra/compose.yaml up -d
   ```

3. Check readiness:

   ```powershell
   docker compose --env-file .env -f infra/compose.yaml ps
   ```

PostgreSQL is reachable only at `127.0.0.1:${POSTGRES_PORT}` and Redis only at
`127.0.0.1:${REDIS_PORT}`. The default host ports are 55432 and 6379
respectively; PostgreSQL itself continues to listen on 5432 in the container.
The named `postgres_data` volume persists database data across restarts.

Inside the Compose network the Postgres hostname is `postgres`. Host-local
Django must use `POSTGRES_HOST=127.0.0.1` and the published `POSTGRES_PORT`.

### Stop infrastructure

Stop containers while keeping PostgreSQL data:

```powershell
docker compose --env-file .env -f infra/compose.yaml down
```

To remove the persistent database volume as well (this permanently deletes all
local PostgreSQL data), run `docker compose --env-file .env -f infra/compose.yaml down -v`.

## Backend (Phase 1B)

Django 6 + Django REST Framework, configured from the repository-root `.env`.

### Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
```

### Run

With infrastructure already up:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

Health check (no auth):

```text
GET http://127.0.0.1:8000/api/v1/health/
```

Expected response shape:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-11-05T18:26:38.885012Z"
}
```

### Tests and checks

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py test tests -v 2
```

### Environment variables used by Django

| Variable | Purpose |
|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Database credentials (shared with Compose) |
| `POSTGRES_HOST` | `127.0.0.1` for host-local Django; `postgres` only inside Compose |
| `POSTGRES_PORT` | Host-mapped port (default `55432`) |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | Debug flag |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins (Vite defaults to `:5173`) |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins |

## Background worker (Phase 1D)

Celery reuses the Phase 1A Redis service as broker (DB 0) and result backend
(DB 1). Configuration is environment-based (`REDIS_*`, derived in
`config/settings/base.py`); no secret is hardcoded.

### Run a worker

With infrastructure up and backend dependencies installed:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A config worker --loglevel=info --pool=solo
```

`--pool=solo` is required on Windows (the prefork pool is not supported there).

### Verify the wiring

The foundation probe task is `core.ping`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.dev'); django.setup(); from apps.core.tasks import ping; print(ping.delay().get(timeout=20))"
```

Expected output: `pong`.

### Celery environment variables

| Variable | Purpose |
|---|---|
| `REDIS_HOST` / `REDIS_PORT` | Redis host/port shared with Compose (defaults `127.0.0.1:6379`) |
| `REDIS_PASSWORD` | Redis password (required by the Phase 1A service) |
| `CELERY_BROKER_DB` / `CELERY_RESULT_DB` | Redis DB index for broker / results (defaults `0` / `1`) |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Optional full-URL overrides (e.g. `redis://redis:6379/0` for a future in-Compose worker) |

No domain or NASA tasks exist yet; `core.ping` only proves the worker and broker work.

## Frontend (Phase 1C)

React 19 + TypeScript + Vite. The app renders a backend-connectivity check
against `GET /api/v1/health/` and reads the API base URL from
`VITE_API_BASE_URL`.

### Setup

```powershell
cd frontend
copy .env.example .env
npm install
```

`frontend/.env.example` sets `VITE_API_BASE_URL=http://127.0.0.1:8000`. Only
public browser-safe values belong in Vite env files; never put Django secrets,
database passwords, or NASA credentials here.

### Run

With infrastructure and the Django backend already running:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/`. The page shows the configured API base URL and
the health `status`, `database`, and `timestamp` returned by Django.

### Build, lint, and test

```powershell
cd frontend
npm run build   # tsc -b && vite build
npm run lint    # oxlint
npm test        # vitest
```

## Not in this phase

- Domain models, NASA integrations, auth, recommendations (Phase 2+)

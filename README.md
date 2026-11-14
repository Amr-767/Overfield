# Overfield

**Explore Beyond the Field.**

Overfield transforms NASA Earth observation data and agricultural context into understandable environmental insights that help farmers explore more resilient agricultural decisions.

**NASA Space Apps Challenge 2026** — *Field Shift: Adapting Farms with NASA Data*

**Initial demonstration region:** Gharbia Governorate, Egypt (`EG-GH`)

## Project team

- **Amr** — Backend, full-stack architecture, NASA integration and deployment
- **Haneen** — Frontend, React, UI/UX and frontend integration

## Agricultural knowledge status (Phase 5.1–5.3)

The backend has a source-specific crop-knowledge catalogue, a safe repeatable dataset
importer, and a fail-closed rotation **evidence-readiness** engine. Crop knowledge is
kept separate from NASA environmental observations and retains
dataset/version/publisher/licence, record-level evidence, raw values and units, and
geographic applicability.

The production catalogue is currently empty: no individual USDA Ag Data Commons
dataset has been approved in this repository, and Overfield does not manufacture crop
traits or use U.S.-specific evidence as an Egyptian calendar. Rotation requests
therefore return `INSUFFICIENT_EVIDENCE` with no alternatives rather than a confident
recommendation. The engine emits **no scores or ranking**, and flavour-specific
benefits (yield, profit, soil outcomes) are never claimed.

> **Review gate is not yet enforced by the engine.** A source may claim
> `validation_status = VALID`; `approval_status` stays `PENDING` until a reviewer acts,
> but candidate selection currently gates on the source claim. Closing this is a
> Phase 6 gate item, tracked in [`docs/PHASE_5_STATUS.md`](docs/PHASE_5_STATUS.md).

```powershell
# JWT required; farm endpoints are owner-scoped
curl "http://127.0.0.1:8000/api/v1/crops/?region_code=EG-GH" -H "Authorization: Bearer $TOKEN"
curl -X POST "http://127.0.0.1:8000/api/v1/farms/4/recommendations/" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"planning_seasons":4}'
```

See [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md) for the approval and import
requirements and [`docs/PHASE_5_STATUS.md`](docs/PHASE_5_STATUS.md) for verification
evidence and known limitations.

## Prerequisites

- Docker Desktop running with Linux containers enabled
- Docker Compose v2 or newer (`docker compose version`)
- Python 3.12+ (Phase 1B verified with Python 3.14 on Windows)
- Node.js 20+ and npm (Phase 1C verified with Node 24 / npm 11)

## Local infrastructure (Phase 1A)

PostgreSQL with PostGIS and Redis run in Docker. From Phase 2 Step 0 the Django
backend also runs in Docker (see "Dockerized backend" below), because GeoDjango
requires native GEOS/GDAL/PROJ libraries. The React/Vite frontend still runs on
the host.

### Start infrastructure

1. Copy `.env.example` to `.env` if it is not already present, and set unique
   local-development passwords and a `DJANGO_SECRET_KEY`. Never commit `.env`.
2. Start the infrastructure services from the repository root (omit `backend`
   here; `up -d` alone would also build and start Django):

   ```powershell
   docker compose --env-file .env -f infra/compose.yaml up -d postgres redis
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

## Dockerized backend (Phase 2 Step 0)

Django 6 + DRF + GeoDjango run inside the `backend` Compose service
(`python:3.14-slim`, GDAL 3.10.3, GEOS 3.13.1, PROJ 9.6.0). See ADR-018 and
`backend/Dockerfile`.

### Start everything

From the repository root:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d --build
```

The first build installs the geospatial libraries and Python dependencies. The
service waits for healthy `postgres` and `redis`, then serves Django on
`http://127.0.0.1:8000` with autoreload enabled. Source edits under `backend/`
restart the server automatically because the directory is bind-mounted.

### Common commands

```powershell
# Service status (backend reports its own health)
docker compose --env-file .env -f infra/compose.yaml ps

# Follow Django logs / autoreload output
docker compose --env-file .env -f infra/compose.yaml logs -f backend

# Django checks, migrations and tests inside the container
docker compose --env-file .env -f infra/compose.yaml exec backend python manage.py check
docker compose --env-file .env -f infra/compose.yaml exec backend python manage.py migrate
docker compose --env-file .env -f infra/compose.yaml exec backend python manage.py test tests -v 2

# Interactive shell
docker compose --env-file .env -f infra/compose.yaml exec backend python manage.py shell

# Rebuild after changing backend/requirements.txt or the Dockerfile
docker compose --env-file .env -f infra/compose.yaml up -d --build backend

# Infrastructure only (no Django) - same as Phase 1A
docker compose --env-file .env -f infra/compose.yaml up -d postgres redis
```

Inside the Compose network Django uses `POSTGRES_HOST=postgres`,
`POSTGRES_PORT=5432` and `REDIS_HOST=redis`; the Compose service overrides the
host-oriented values in `.env`. Public ports stay bound to `127.0.0.1`.

### GeoDjango smoke check

```powershell
docker compose --env-file .env -f infra/compose.yaml exec backend python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.dev'); import django; django.setup(); from django.contrib.gis.geos import GEOSGeometry; from django.contrib.gis.gdal import gdal_version; print('GDAL', gdal_version()); print(GEOSGeometry('POLYGON((0 0,0 1,1 1,1 0,0 0))').area)"
```

### Celery worker

The worker must run in the same image as Django (same settings, same native
libraries):

```powershell
docker compose --env-file .env -f infra/compose.yaml exec backend celery -A config worker --loglevel=info
```

---

## Backend on the host (Phase 1B, superseded)

> Historical reference only. From Phase 2 Step 0 the backend runs in Docker
> because the host has no GDAL/GEOS; the host venv is not a supported runtime.

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
| `POSTGRES_HOST` | `127.0.0.1` for host tools; the Compose `backend` service overrides it to `postgres` |
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

Domain tasks exist from Phase 3 onward: `earth_data.ingest_farm_environment` performs the NASA POWER
ingestion; `core.ping` remains the infrastructure probe.

## Frontend (Phase 2)

React 19 + TypeScript + Vite with React Router 7, TanStack Query 5 and
Leaflet 1.9 + Leaflet-Geoman. The app provides JWT sign-in/registration and the
five-step farm onboarding flow.

### Routes

| Route | Screen |
|---|---|
| `/` | Landing page + backend status |
| `/login`, `/register` | Sign in / create account |
| `/onboarding` | Profile → Farm details → Draw your farm → Farm information → Review |
| `/farms` | Saved farms (owner only, loaded from the API) |
| `/farms/:id` | Saved farm detail with boundary map, area and farmer context |

Protected routes redirect to `/login` and return to the requested page after signing in.
Onboarding progress is kept in `sessionStorage` per tab so a reload resumes the same step.

### Setup

```powershell
cd frontend
copy .env.example .env
npm install
```

`frontend/.env.example` sets `VITE_API_BASE_URL=http://127.0.0.1:8000`. Only
public browser-safe values belong in Vite env files; never put Django secrets,
database passwords, or NASA credentials here.

The map uses OpenStreetMap raster tiles by default with visible attribution
(follow the OSM tile usage policy — no bulk downloads). Override the tile source
if needed:

```text
VITE_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_TILE_ATTRIBUTION=&copy; OpenStreetMap contributors
```

### Run

With the Docker backend already running (`http://127.0.0.1:8000`):

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/`, create an account, then add a farm. The boundary
toolbar draws a polygon; the area shown comes from the backend
(`POST /api/v1/farms/validate-boundary/`), not from the browser. If you cannot
draw a boundary, switch to "Just a location" and enter an approximate area — it
is stored as farmer-reported with low spatial precision.

### Build, lint, and test

```powershell
cd frontend
npm run build   # tsc -b && vite build
npm run lint    # oxlint
npm test        # vitest (61 tests)
```

## Environmental indicators (Phase 4)

Four decision-support indicators are computed on demand from stored observations and the farmer
context — no new tables, no provider calls at request time:

| Indicator | What it reports |
|---|---|
| **WATER** | rainfall total over covered days, rainy days (≥ 1.0 mm), max daily rainfall, longest observed dry run |
| **HEAT** | mean / mean-max / mean-min air temperature, hot days (≥ 35 °C), very hot days (≥ 40 °C), cool nights (≤ 5 °C) |
| **SOIL** | per-property soil report (pH band, organic carbon, N/P/K, texture) with provenance and sample age |
| **MARKET** | `UNAVAILABLE` — no verified local farm-gate price source exists |

```powershell
# JWT required; owner only
curl "http://127.0.0.1:8000/api/v1/farms/4/environment/current/?window_days=30"   -H "Authorization: Bearer $TOKEN"
```

`current` means **the latest available observation**, not real-time weather: the window ends at the
newest stored observation and the response reports `latest_observation`, `age_days` and `freshness`.
No 0–100 scores are produced in Phase 4; missing data is reported as missing, never as zero.

Methodology, thresholds and limitations: [`docs/ENVIRONMENTAL_INDICATORS.md`](docs/ENVIRONMENTAL_INDICATORS.md).
API contract: [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) §4.

### Data sources

**NASA POWER is the only integrated environmental data source.** It supplies the daily `T2M`,
`T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M` and `ALLSKY_SFC_SW_DWN` series behind WATER and
HEAT. It is reanalysis/assimilation data for a grid cell, not an on-farm measurement.

GPM IMERG, SMAP, Landsat Collection 2, Sentinel-2, HLS, MODIS/VIIRS, ECOSTRESS, SRTM, GLDAS, ERA5,
GAEZ and GEDI have been **evaluated but are not integrated**. U.S.-only resources (Web Soil Survey,
SSURGO/STATSGO2, Cropland Data Layer, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS Market News, NASS
QuickStats, OpenET, LANDFIRE) do not cover Gharbia and must not be used as demo or fallback data.

SOIL reports only farmer-provided `FarmerContext` measurements with provenance, and MARKET remains
`UNAVAILABLE` because no verified local farm-gate price source exists. Product versions, resolutions,
access methods and limitations:
[`docs/HACKATHON_DATA_SOURCE_MATRIX.md`](docs/HACKATHON_DATA_SOURCE_MATRIX.md).

## Not implemented yet

- Scenario simulation and strategy comparison (Phase 6)
- Frontend screens for the environmental indicators and the summary endpoint
- Zones editing UI, farm editing UI, and farm deletion from the SPA
- Leaderboards, rewards and verification (Phase 8)

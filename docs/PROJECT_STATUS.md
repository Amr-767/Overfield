# Overfield — Project Status

**Last updated:** 2026-11-14
**Current phase:** Phase 5.3 — Crop rotation evidence engine (published); Phase 6 setup prepared
**Phase status:** ✅ Phase 4A–4F complete. ✅ Phase 5.1/5.2 catalogue and Phase 5.3 fail-closed rotation assessment verified in the Docker/PostGIS runtime (325 backend tests, 61 frontend tests). Production rotation options remain unavailable until approved regional crop evidence/calendar exists. See [`PHASE_5_STATUS.md`](PHASE_5_STATUS.md).

> **Phases 1–3 are complete and merged into `develop`.** Phase 1 delivered the Docker infrastructure,
> Django/DRF foundation, React/Vite frontend and the Celery worker. Phase 2 delivered accounts, JWT, the
> `Farm`/`FarmZone`/`FarmerContext`/`FarmCropHistory` models, owner-scoped APIs, geodesic area calculation
> and the five-step onboarding wizard. Phase 3 delivered the NASA POWER client, environmental data models,
> Celery ingestion and the observation REST API. **Phase 4** added the WATER/HEAT/SOIL/MARKET indicator
> engine, the environmental summary endpoint and `ENVIRONMENTAL_INDICATORS.md`. **Phase 4F** aligned the
> documentation with the NASA Space Apps 2026 dataset audit and added
> [`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md). Only **NASA POWER** is integrated.

## Repository Audit (current checkout)

| Item | Actual status |
|---|---|
| Repository | Git repository initialized; Phase 5 branch is `phase/5-rotation-engine` |
| Local branches | `main`, `develop`, `phase/0-documentation-review`, `phase/1-foundation`, `phase/2-farm-management`, `phase/3-nasa-integration`, `phase/4-environmental-engine`, `phase/5-rotation-engine`, `phase/6-simulation` |
| Remote | `origin` → `https://github.com/Amr-767/nasa.git` (Phase 4 baseline); `overfield` → `https://github.com/Amr-767/Overfield.git` (rebranded Overfield repository, receives Phase 5 and Phase 6 branches) |
| Backend (`backend/`) | Django 6.0.10 + GeoDjango (`django.contrib.gis`) with the PostGIS backend; `config/` split settings, DRF + SimpleJWT, CORS, `apps.core` (health, `core.ping`), `apps.accounts` (profile/auth), `apps.farms` (farms/zones/context), `apps.earth_data` (POWER provider, models, Celery ingestion, REST API), `apps.agronomy` (source-specific agricultural dataset registry, audit imports, crop traits, read APIs), `apps.indicators` (WATER/HEAT/SOIL/MARKET + summary API), `domain_services` (geometry). Runs in the `backend` Compose service (ADR-018) |
| Frontend (`frontend/`) | React 19 + TypeScript + Vite + React Router 7 + TanStack Query 5 + Leaflet 1.9/Leaflet-Geoman: auth screens, 5-step onboarding wizard, farm list/detail, rotation explorer, env-driven API client with JWT handling. No environmental-indicator UI yet |
| Documentation (`docs/`) | Master Handoff, Phased Coding Playbook, Phase 0 docs, Git workflow, review, risk register, environmental-indicator methodology and the NASA data-source matrix present |
| `README.md` | Documents infrastructure, backend, worker and frontend setup plus the Phase 4 indicator API and the integrated-data-source scope |
| `.gitignore` | Present; `.env` and `.venv/` ignored |
| `.env.example` | Present with Postgres/Redis/Django placeholders; local `.env` is ignored |
| Dependencies | Backend pinned in `backend/requirements.txt` (Celery + redis included); frontend pinned in `frontend/package.json` + `package-lock.json`; virtualenv and `node_modules` are local-only |
| Tests | Backend: **325 Django tests** passing. Frontend: **61 Vitest tests** passing |
| Frontend deps | `react-router-dom`, `@tanstack/react-query`, `leaflet`, `react-leaflet`, `@geoman-io/leaflet-geoman-free`; test-only `jsdom`, `@testing-library/react`, `@testing-library/user-event` |
| Database | Docker Compose `postgis/postgis:17-3.5` (PostgreSQL 17.5, PostGIS 3.5.2); Django uses `django.contrib.gis.db.backends.postgis` |
| Backend runtime | Docker image `python:3.14-slim` (Debian 13) with GDAL 3.10.3, GEOS 3.13.1, PROJ 9.6.0; `backend/Dockerfile` + `backend/.dockerignore`; the host venv is editor-only |
| Redis | Local Docker Compose: `redis:7.4.12`; used by Celery (Phase 1D) as broker (DB 0) and result backend (DB 1) |

### Documentation inventory

- [`AgroSpace_Quest_Master_Agent_Handoff.md`](AgroSpace_Quest_Master_Agent_Handoff.md) — historical product specification (former project name)
- [`AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md`](AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md) — historical phased execution guide (former project name)
- [`AgroSpace_Quest_Phase0_Review.md`](AgroSpace_Quest_Phase0_Review.md) — historical review (former project name)
- [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)
- [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md)
- [`API_CONTRACTS.md`](API_CONTRACTS.md)
- [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md)
- [`ENVIRONMENTAL_INDICATORS.md`](ENVIRONMENTAL_INDICATORS.md)
- [`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md)
- [`PHASE_5_STATUS.md`](PHASE_5_STATUS.md)
- [`PHASE_6_SLICE_PLAN.md`](PHASE_6_SLICE_PLAN.md)
- [`PHASE_4_RELEASE_AUDIT.md`](PHASE_4_RELEASE_AUDIT.md)
- [`RISK_REGISTER.md`](RISK_REGISTER.md)
- [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md)

## Phase 0 Completion

- [x] Master requirements summarized into a feasible P0 journey
- [x] Repository audit reconciled with the actual checkout
- [x] Modular architecture and staged app boundaries documented
- [x] Planning documents and risk register created
- [x] No domain feature implementation started in Phase 0

## Phase 1A Completion — Local Development Infrastructure

- [x] Docker Compose `infra/compose.yaml` with pinned `postgis/postgis:17-3.5` and `redis:7.4.12`
- [x] Localhost-only port bindings, env-based credentials, health checks, named volume
- [x] `.env.example` and ignored local `.env`
- [x] Services verified healthy

**Boundary:** Phase 1A stopped before application scaffolding.

## Phase 1B Completion — Django Backend Foundation

- [x] Django 6.0 project initialized under `backend/` with `config/` package
- [x] Split settings: `config.settings.base` / `dev` / `prod`
- [x] Environment loading from repository-root `.env` (shared with Compose)
- [x] PostgreSQL connection using Phase 1A `POSTGRES_*` variables; host-local `POSTGRES_HOST=127.0.0.1`
- [x] Django REST Framework configured
- [x] `django-cors-headers` configured for Vite origins (`localhost:5173`)
- [x] API versioning prefix `/api/v1/`
- [x] Public health endpoint `GET /api/v1/health/`
- [x] Initial Django migrations applied to the Compose PostgreSQL database
- [x] Starter tests added and executed
- [x] README backend setup instructions documented
- [x] No unused domain apps scaffolded (ADR-008)
- [x] No GeoDjango models yet; engine remains standard PostgreSQL against PostGIS image
- [x] Compose file left unchanged

### Verification performed (2026-11-05)

| Check | Command / action | Result |
|---|---|---|
| System checks | `python manage.py check` | No issues |
| Migrations | `python manage.py migrate` | Applied Django built-in migrations successfully |
| Tests | `python manage.py test tests -v 2` | 5 passed |
| Health endpoint | `GET http://127.0.0.1:8000/api/v1/health/` | `200` with `status=healthy`, `database=connected` |
| Infrastructure | `docker compose ... ps` | `postgres` and `redis` healthy |

## Phase 1C Completion — React Frontend Foundation

- [x] Vite + React + TypeScript project under `frontend/` (npm with committed `package-lock.json`)
- [x] Environment-driven API client reading `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`)
- [x] Frontend uses the `/api/v1/` version path
- [x] Backend connectivity check against `GET /api/v1/health/` with loading, connected, and error states
- [x] `frontend/.env.example` present; local `frontend/.env` ignored; no secrets in Vite env
- [x] Frontend `.gitignore` (node_modules, dist, env files; keeps `.env.example`)
- [x] oxlint configured and passing with no warnings
- [x] Starter Vitest tests for the API client and health connectivity
- [x] Root and frontend README setup/run/build/lint/test instructions
- [x] No domain features, routing, or auth added (out of Phase 1C scope)

### Verification performed (2026-11-05)

| Check | Command / action | Result |
|---|---|---|
| Production build | `npm run build` (`tsc -b && vite build`) | Passed (22 modules transformed) |
| Lint | `npm run lint` (oxlint) | Passed, 0 warnings |
| Frontend tests | `npm test` (vitest) | 7 passed |
| Dev server | `npm run dev` | Served `http://127.0.0.1:5173/` (HTTP 200) |
| Backend health | `GET /api/v1/health/` | `200`, `status=healthy`, `database=connected` |
| CORS | request with `Origin: http://localhost:5173` | `access-control-allow-origin: http://localhost:5173` |
| Backend tests | `python manage.py test tests -v 2` | 5 passed |

A headless-browser test was not run. Connectivity was verified by confirming the
health response and the CORS allow-origin header for the Vite origin, supported by
unit tests for the API client parsing logic.

## Phase 1D Completion — Celery Background Worker Foundation

- [x] `celery[redis]` added to `backend/requirements.txt` (Celery 5.7, redis 8.1 on Python 3.14)
- [x] `config/celery.py` defines the `agrospace` Celery app and loads `CELERY_*` from Django settings
- [x] `config/__init__.py` imports the app so it loads with Django
- [x] Environment-based broker/result config reusing Phase 1A Redis (`REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`; DB 0/1)
- [x] Optional `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` overrides for a future in-Compose worker
- [x] Task discovery via `app.autodiscover_tasks()`; `apps/core/tasks.py` provides `core.ping`
- [x] No new container or Compose change; credentials stay in `.env` (no hardcoded secrets)
- [x] Tests added (7) and README worker startup/verification instructions documented
- [x] No NASA integrations, crop logic, or domain tasks added

### Verification performed (2026-11-05)

| Check | Command / action | Result |
|---|---|---|
| System checks | `python manage.py check` | No issues |
| Backend tests | `python manage.py test tests -v 2` | 12 passed (5 prior + 7 Celery) |
| Worker startup | `celery -A config worker --loglevel=info --pool=solo` | Connected to `redis://127.0.0.1:6379/0`; discovered `core.ping`; ready |
| End-to-end task | `ping.delay().get(timeout=20)` | `pong` (worker logged `succeeded … 'pong'`) |
| Broker/result | worker log | transport `redis://…/0`, results `redis://…/1` |

## Phase 1E Completion — Full Foundation Integration Verification

- [x] Docker Compose config validates; PostGIS and Redis containers healthy
- [x] PostgreSQL accepting connections; PostGIS 3.5.2 present; migrations applied
- [x] Redis authentication + PING verified from the host using Django settings
- [x] Django system checks clean; health endpoint `200` (healthy/connected) and `503` (unhealthy/unavailable) contracts verified
- [x] CORS allow-origin confirmed for the Vite origin
- [x] React production build succeeds; API base URL and `/api/v1/health/` present in the bundle
- [x] Celery worker connects to Redis and executes `core.ping` through the broker
- [x] Backend (13) and frontend (7) tests pass
- [x] Environment keys consistent between `.env` and `.env.example`
- [x] No features added; no Phase 2 work started

### Verification performed (2026-11-05)

| Check | Command / action | Result |
|---|---|---|
| Compose config | `docker compose --env-file .env -f infra/compose.yaml config --quiet` | Valid |
| Services | `docker compose … ps` | postgres + redis `Up (healthy)` |
| PostGIS | `SELECT postgis_full_version()` | PostGIS 3.5.2 on PostgreSQL 17 |
| Migrations | `python manage.py migrate --check` | All applied |
| Redis | `redis-cli ping` / host `redis.ping()` | `PONG` / `True` |
| Django checks | `python manage.py check` | No issues |
| Health 200 | `GET /api/v1/health/` | `200`, `healthy`/`connected` |
| Health 503 | connection-failure test (patched) | `503`, `unhealthy`/`unavailable` |
| CORS | `Origin: http://localhost:5173` | `access-control-allow-origin` present |
| Frontend build | `npm run build` | Passed; bundle contains the API base URL |
| Frontend lint | `npm run lint` | 0 warnings |
| Backend tests | `python manage.py test tests -v 2` | 13 passed |
| Frontend tests | `npm test` | 7 passed |
| Celery end to end | worker + `ping.delay().get()` | `pong` |

Note: a headless-browser test was not run. Frontend↔backend connectivity is verified via
the live health response, the CORS allow-origin header, the bundled API URL, and the
client unit tests.

## Phase 2 Step 0 Completion — GeoDjango and Mapping Architecture

**Status:** ✅ COMPLETE (environment + decisions only; no Phase 2 features implemented)

| Verification | Result |
|---|---|
| `django.contrib.gis` import | ✅ |
| `GEOSGeometry` create/validate (SRID 4326) | ✅ `Polygon`, valid, WKT round-trip |
| GDAL detected | ✅ 3.10.3 (`libgdal.so.36`), above Django's 3.9 minimum |
| GEOS detected | ✅ 3.13.1 CAPI 1.19.2 (`libgeos_c.so.1`) |
| PROJ available | ✅ `SpatialReference(4326)` resolves; `/usr/share/proj` present |
| PostGIS backend recognized | ✅ `django.contrib.gis.db.backends.postgis.base.DatabaseWrapper` |
| Connects to existing PostGIS DB | ✅ `postgres:5432/agrospace` inside Compose |
| PostGIS extension available | ✅ PostGIS 3.5.2 on PostgreSQL 17.5; 8,500 SRID rows |
| `ST_Area(geometry::geography)` | ✅ 3.7882 ha for a ~0.002° box (plausible; geodesic, not planar degrees) |
| Health endpoint | ✅ `200 {"status":"healthy","database":"connected"}` |
| Phase 1 regression tests | ✅ 13/13 passed inside the container |
| Autoreload | ✅ server restarts on source change (StatReloader) |

**Authentication compatibility (isolated, disposable venv, exact pins):**
`djangorestframework-simplejwt==5.5.1` + `PyJWT 2.15.1` with `Django 6.0.10` and
`djangorestframework 3.18.3` — `manage.py check` clean, `POST /token/` → 200
access+refresh, Bearer-protected view → 200, `POST /token/refresh/` → 200,
unauthenticated request → 401. **SimpleJWT is compatible; no architecture change
needed.** Note: PyJWT warns when the HMAC signing key is under 32 bytes — the
project `DJANGO_SECRET_KEY` must stay long.

**Decisions recorded:** ADR-017 (Leaflet + Leaflet-Geoman Free), ADR-018
(Dockerized Django for GeoDjango; supersedes the run-location part of ADR-014).

**Not done in Step 0:** custom user model, registration/JWT endpoints, farm models,
farm APIs, map UI, soil forms, NASA integrations.

## Phase 2 Backend Completion — Accounts, Farms, Zones, Farmer Context

**Status:** ✅ COMPLETE (backend only; frontend not started)

### Models and migrations

| App | Model | Purpose |
|---|---|---|
| `accounts` | `FarmerProfile` | One-to-one profile on the built-in `auth.User` (`display_name`, `preferred_language`) — ADR-019 |
| `farms` | `Farm` | Owner, name, country/region, `MultiPolygonField` boundary, `PointField` location, backend area, `area_source`, `geometry_source`, timestamps |
| `farms` | `FarmZone` | Optional farmer-created sub-area, must lie inside the farm |
| `farms` | `FarmerContext` | Soil (pH, texture, organic carbon, N/P/K, depth, lab, method, date), water (availability/type/reliability), priorities, constraints |
| `farms` | `FarmCropHistory` | Ordered season/crop history with per-entry provenance |

Migrations: `accounts.0001_initial`, `farms.0001_initial` — applied to the existing database; **no reset, no data loss**.

Verified schema: `boundary geometry(MultiPolygon,4326)`, `location geometry(Point,4326)`, GiST indexes on both
(`farms_farm_boundary_e269c84a_id`, `farms_farm_location_80d6b65e_id`), plus check constraints
`farm_has_boundary_or_location`, `farm_area_positive`, `farm_zone_area_positive`.

### Endpoints (all `/api/v1/`)

| Method + path | Auth | Behaviour |
|---|---|---|
| `POST /auth/register/` | public | Creates user + profile in one transaction; duplicate username/email and weak passwords rejected |
| `POST /auth/token/`, `POST /auth/token/refresh/` | public | JWT access (60 min) + refresh (7 days) |
| `GET/PATCH/PUT /me/` | JWT | Own profile; email uniqueness enforced |
| `GET/POST /farms/` | JWT | List (paginated) / create; owner-filtered |
| `GET/PATCH/PUT/DELETE /farms/{id}/` | JWT | Owner only; cross-user access → `404` |
| `POST /farms/validate-boundary/` | JWT | Pre-submit geometry validation, returns geodesic area |
| `GET/POST /farms/{id}/zones/` | JWT | List / create; containment enforced |
| `GET/PUT/PATCH /farms/{id}/context/` | JWT | Read/update farmer inputs |

Global DRF defaults now require authentication; only health, registration and token endpoints opt out.

### Spatial calculation

- Storage/interchange SRID: **4326** (`MultiPolygonField`, `PointField`)
- Area: PostGIS `ST_Area(ST_GeomFromEWKB(geom)::geography) / 10000` → hectares, quantised to 4 dp
- Known test polygon (Nile Delta, ~0.0021° × 0.0017°): **3.7882 ha**; the same ring is 3.57e-06 if degrees are treated as planar, so the test asserts hectares are geodesic
- Validation rejects: wrong type, empty coordinates, unclosed rings, rings < 4 positions, out-of-range lon/lat, self-intersections, zero area, and areas above 10,000 ha
- GeoJSON coordinate order is asserted by checking the created farm's centroid (`lon 30.95115`, `lat 30.79095`)
- Client-supplied `area_hectares` is ignored (tested)

### Verification executed

| Check | Result |
|---|---|
| `manage.py check` | ✅ no issues |
| `makemigrations` / `migrate` | ✅ `accounts.0001`, `farms.0001` applied |
| `manage.py test tests` | ✅ **76/76 passed** |
| Live HTTP smoke test (register → token → create farm → context) | ✅ `201/200`, area `3.7882`, `spatial_precision HIGH` |
| Live invalid boundary | ✅ `400` with self-intersection message |
| Unauthenticated `/farms/` | ✅ `401` |
| Smoke data cleanup | ✅ cascade delete verified; 0 users/farms remain |

## Phase 2 Frontend Completion — React Farm Onboarding

**Status:** ✅ COMPLETE (implementation + verification; not committed)

### Screens

| Route | Purpose |
|---|---|
| `/` | Landing page with CTAs and the Phase 1 backend status panel |
| `/login`, `/register` | JWT sign-in and farmer registration |
| `/onboarding` | 5-step wizard: Profile → Farm → Boundary → Details → Review |
| `/farms` | Owner's farms loaded from `GET /api/v1/farms/` |
| `/farms/:id` | Saved farm: boundary map, area + source, soil/water/crops/priorities, zones |
| `*` | Not-found page |

Protected routes redirect to `/login` and return to the requested page after sign-in.

### Onboarding flow

1. **Profile** — display name, optional email, language; saved with `PATCH /me/` before continuing.
2. **Farm details** — name, country code, region, timezone with client validation.
3. **Draw your farm** — Leaflet map with Geoman draw/edit/remove, or a point-only fallback with a
   farmer-reported area. Area is requested from `POST /farms/validate-boundary/` (debounced) and
   labelled by source; failures surface as an inline message.
4. **Farm information** — optional soil (type, pH, lab, advanced N/P/K/organic carbon/depth/date),
   irrigation and water reliability, crop history rows, priority sliders normalised to weights
   summing to 1, and practical constraints. Unknown values are omitted or sent as `null`.
5. **Review and save** — summary cards with per-section “Edit”, read-only map, explicit
   precision warning for point-only farms, then `POST /farms/` followed by `PATCH /farms/{id}/context/`.

Progress (answers and current step) is stored in `sessionStorage` for the tab and cleared after a
successful save. A page reload resumes at the same step without losing entered data.

### API integration

- Existing `src/api/client.ts` extended with `apiRequest` (method, JSON body, bearer token,
  field-error mapping, single 401 retry through a registered refresh handler).
- Access token in memory; refresh token in `sessionStorage` and exchanged on load (ADR-009
  compromise documented in `tokenStore.ts`).
- Endpoints used: `/auth/register/`, `/auth/token/`, `/auth/token/refresh/`, `/me/`, `/farms/`,
  `/farms/{id}/`, `/farms/validate-boundary/`, `/farms/{id}/context/`.
- No hardcoded farm data; the list and detail pages read from the database.

### Map

Leaflet 1.9 + `react-leaflet` 5 + `@geoman-io/leaflet-geoman-free` 2 (ADR-017). OSM raster tiles
by default with visible attribution; tile URL and attribution are configurable via
`VITE_TILE_URL` / `VITE_TILE_ATTRIBUTION`. Geoman toolbar provides polygon draw, vertex edit and
removal; `layer.toGeoJSON()` supplies the submitted geometry in `[longitude, latitude]` order.
Text search is not provided because the configured tile provider has no keyless search API;
location selection uses map click or browser geolocation.

### Verification executed

| Check | Result |
|---|---|
| `npm run lint` (oxlint) | ✅ 0 warnings |
| `npm test` (vitest) | ✅ **51/51 passed** across 6 files |
| `npm run build` | ✅ `tsc -b` clean, bundle 787.86 kB (226.38 kB gzip) |
| Live API contract check (temporary test, removed) | ✅ register → create farm (area 3.7882 ha, `GEOMETRY_DERIVED`, `HIGH`) → context saved → farm retrieved; invalid boundary correctly returned `400` |
| Production preview | ✅ `/`, `/farms`, `/onboarding` served with SPA fallback and assets at `200` |

Browser-level click-through on real hardware was **not** automated (no headless browser installed);
map interactions are covered by the component stub path plus the live API checks above.

## Phase 2 Integration Audit — End-to-End Verification

**Status:** ✅ PASSED (2026-11-07). Verified with the real React app in real Chrome via Playwright
against the Dockerized Django/PostGIS backend — not with mocked API calls.

### Farmer journey (browser, real UI clicks)

| Step | Result |
|---|---|
| Register Farmer A through the form | ✅ lands on `/onboarding`; profile prefilled |
| Save profile (step 1) | ✅ `PATCH /api/v1/me/ → 200` |
| Farm details (step 2) | ✅ name/region accepted |
| Draw polygon with the Geoman toolbar | ✅ 5 clicks on the real map |
| Area from backend | ✅ `677.01 ha`, labelled “Calculated from your boundary by PostGIS” |
| `POST /farms/validate-boundary/` | ✅ `200` (debounced preview) |
| Farm information (soil/water/crop/constraints) | ✅ clay loam, pH 7.8, irrigation yes/canal, Wheat |
| Save | ✅ `POST /farms/ → 201`, then `PATCH /farms/{id}/context/ → 200` |
| Detail page after redirect | ✅ area, `High — drawn boundary`, pH 7.80, Wheat chip |
| **Reload (F5)** | ✅ farm, boundary and context re-fetched and rendered identically; session restored via refresh token |
| Draft cleared after save | ✅ `sessionStorage` empty |

**Browser console:** no unexpected errors; no unexpected failed API calls (the single `404` is Farmer B's
blocked access, which is the expected result).

### Geospatial verification (14 checks)

Valid polygon accepted (3.7882 ha for the known ring) · stored as `MultiPolygon` ·
`area_source=GEOMETRY_DERIVED` · `spatial_precision=HIGH` · centroid `[lon, lat]` = `[30.95115, 30.79095]` ·
latitude > 90 rejected (coordinate-order/range guard) · unclosed ring rejected with
“geometry is not closed” · self-intersecting polygon rejected · area > 10,000 ha rejected · empty
coordinates rejected · **client-supplied `area_hectares=999999` ignored** (stored 3.7882) ·
point fallback saved as `FARMER_REPORTED`/`LOW` · point fallback without an area rejected.

**PostGIS row for the browser-created farm:** `SRID 4326`, `ST_MultiPolygon`, 5 vertices, `ST_IsValid = true`,
`ST_Area(boundary::geography)/10000 = 677.0070` — identical to the API value. GiST indexes present on
`farms_farm.boundary`, `farms_farm.location`, `farms_farmzone.boundary`.

### Two-user permission matrix (12 checks)

Farmer B (real second account, real JWT) against Farmer A's farm: list → empty (`count 0`), retrieve → `404`,
PATCH → `404`, DELETE → `404`, context read → `404`, context write → `404`, zones list → `404`,
zone create → `404`. A's farm was unchanged afterwards. `/me/` returns only the caller's profile.
Invalid token → `401`; unauthenticated list → `401`. In the browser, Farmer B opening A's farm URL sees the
“Farm not found” banner and an empty farm list.

### Defects found and fixed during the audit

| # | Defect | Impact | Fix |
|---|---|---|---|
| 1 | React Query cache was not cleared on identity change | After an account switch the previous farmer's cached farms were served to the new user (incorrect list; potential short-lived data exposure) | `queryClient.clear()` on login/register/logout + draft/step reset on logout (`AuthProvider`), covered by `AuthProvider.test.tsx` |
| 2 | Duplicate React `key` in the soil/water `<option>` lists | Console error “Encountered two children with the same key”; could duplicate or drop options | Keys now use `value::label` (`FarmInfoStep`) |

No other Phase 2 defects were found. No schema, migration or contract changes were required.

### Quality gates

`manage.py check` clean · `makemigrations --check` → no changes · migrations `accounts.0001`,
`farms.0001` applied · backend **76/76 tests** · frontend **53/53 tests** · `npm run lint` 0 warnings ·
`npm run build` succeeds (788.31 kB JS / 226.50 kB gzip) · Docker stack healthy throughout.

### Known behaviours (documented, not defects)

- API paths must end with `/`; a slashless `PATCH`/`DELETE` hits Django `APPEND_SLASH` and returns `500`.
  The SPA always uses trailing slashes.
- Cross-user access returns `404` (not `403`) by design, so farm existence is not disclosed.

## Phase 3B Completion — NASA POWER Client

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

`backend/apps/earth_data/providers/` implements a reusable, typedd NASA POWER Daily Point client.
No models, migrations, Celery tasks, endpoints or frontend changes were made in this slice.

| Concern | Implementation |
|---|---|
| HTTP | `power_transport.py` uses stdlib `http.client` with **separate connect (10 s) and read (30 s) timeouts** and injectable `PowerTransport` protocol; no new dependency |
| Request | `build_request_url` always sends `community=AG`, `format=JSON`, `time-standard=UTC`, `YYYYMMDD` dates |
| Validation | coordinates (±90/±180), `start <= end`, no future dates, ≥1981-01-01, per-parameter first availability (solar 1984-01-01), ≤20 params, no duplicates, verified codes only — all **before** any network call |
| Retries | 1 + `max_retries` attempts, exponential backoff, `Retry-After` honoured (seconds or HTTP-date) and capped, retry only on `429/500/502/503/504` and timeouts; `4xx` fails immediately |
| Errors | `PowerConfigurationError`, `PowerRequestError`, `PowerTransientError`, `PowerResponseError` with `.code`, `.details`, `.as_dict()` |
| Parsing | pure `parse_daily_response`: asserts returned `time_standard` matches the request, requires units per parameter, treats `-999.0`/`null` as **missing (`None`)**, drops out-of-range dates, preserves units/longname/product/sources/api version/returned coordinates |
| Repeat protection | TTL cache (default 900 s, 64 entries) keyed by rounded coordinates + range + parameter set |
| Logging | warnings carry attempt/status/provider only — never the query string or coordinates |

**Tests:** `backend/tests/test_power_client.py` — **30 tests**, all mocked (no network): parsing,
multi-parameter, missing values, malformed payloads, unit/time-standard mismatch, invalid dates and
coordinates, unknown/duplicate/too-many parameters, solar availability guard, URL composition,
timeouts, 429 with numeric and HTTP-date `Retry-After`, 5xx retries, permanent 4xx, cache hit/expiry/bypass.

**Full suite:** **106 backend tests OK** (76 existing + 30 new); `manage.py check` clean;
`makemigrations --check` → no changes. Manual live check (not part of the suite): 2024-01-01…07 at
30.79/30.95 returned `v2.10.3`, sources `MERRA2/SYN1DEG/POWER`, T2M 16.15 °C, PRECTOTCORR 0.0 mm/day,
no missing values.

## Phase 3C Completion — Environmental Data Models and Persistence

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Storage decision: structured rows, not JSON

Each daily value is one `EnvironmentalObservation` row. Chosen over a JSON blob because it lets the
database enforce the `(farm, source, observation_date)` uniqueness (duplicate prevention), makes
time-series/date-range/per-parameter queries plain SQL for Phase 4–5, and keeps units and provenance
on a foreign key rather than re-parsed JSON. Values are `Decimal(10, 4)` (not float) so repeated
imports and later sums do not drift; coordinates are `Decimal(9, 6)`.

### Models (`apps/earth_data/models.py`)

| Model | Purpose / key fields |
|---|---|
| `DatasetSource` | Provider parameter catalogue: `provider`, `product`, `parameter_code`, `long_name`, `units`, `community`, `temporal_resolution`, `time_standard`, `data_category`, `daily_aggregation`, `native_resolution_note`, `first_available_date`, `attribution`, `docs_url`, `access_date`, `is_active`. Unique on `(provider, parameter_code, community, time_standard)`. |
| `DataFetchJob` | Fetch history: UUID pk, `farm`, `requested_by`, `status` (PENDING/RUNNING/SUCCEEDED/PARTIALLY_SUCCEEDED/FAILED), requested range + parameters, **requested** lon/lat and `request_geometry_source`, **returned** lon/lat/elevation, `api_name`/`api_version`/`source_products`/`time_standard`/`fill_value`, `days_requested/stored/missing`, `error_code`/`error_message`, timestamps + `duration_ms`. |
| `EnvironmentalObservation` | One value per farm/source/day: `value` (nullable), `quality_status` (AVAILABLE/MISSING), `fetch_job`, requested **and** returned coordinates, timestamps. |

**Integrity:** unique `uniq_farm_source_observation_date`; checks `observation_value_matches_quality`
(AVAILABLE ⇔ value not null), coordinate ranges, `fetch_job_range_ordered`; indexes
`obs_farm_date_idx`, `obs_source_date_idx`, `job_farm_created_idx`, `job_status_idx`,
`source_provider_active_idx`; FKs farm→CASCADE, user→SET_NULL, job→SET_NULL, catalogue→PROTECT.

### Services (`apps/earth_data/services.py`)

`start_fetch_job`, `persist_power_response` (bulk idempotent upsert, counted created/updated),
`record_fetch_failure`, `get_farm_series`, `get_farm_observations`. `persist_power_response` accepts
**only** a `PowerResponse` from the NASA client — a client-supplied dict raises `TypeError`, so farmer
input can never be stored as NASA data. Inactive/missing catalogue rows raise `SourceCatalogueError`
before any write.

### Migrations (additive only, inspected before applying)

- `earth_data.0001_initial` — 3 `CreateModel` + 7 constraints/indexes; depends only on `farms.0001`.
- `earth_data.0002_seed_power_sources` — seeds the 7 verified parameters (units, product, category,
  aggregation, first availability, resolution note; solar resolution deliberately blank), idempotent,
  reverse is a no-op so `PROTECT` cannot be violated.

**Data preservation proof** (same database, before → after): users 2→2, profiles 2→2, farms 2→2,
zones 0→0, contexts 1→1, crop rows 2→2, migrations 20→22; new tables `earth_data_*` 7 sources / 0 jobs /
0 observations. No reset, no destructive command.

### Tests

`backend/tests/test_earth_data_persistence.py` — **19 tests**: catalogue seed, job creation, observation
creation/precision, duplicate prevention (service + DB constraint), repeat-import update semantics,
missing values (`-999` → `None` + MISSING + PARTIALLY_SUCCEEDED), provenance links (requested vs returned
coordinates, api version, products), farm isolation, cascade/SET_NULL/PROTECT behaviour, failure
recording, date/parameter queries, inactive-source rejection, non-POWER payload rejection.

**Full suite:** **125 tests OK** (106 previous + 19 new); `manage.py check` clean;
`makemigrations --check` → no changes.

## Phase 3D Completion — Celery Background Ingestion

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Task

| Item | Value |
|---|---|
| Task name | `earth_data.ingest_farm_environment` |
| Module | `backend/apps/earth_data/tasks.py` (discovered by the existing `config.celery` app) |
| Signature | `(farm_id, start=None, end=None, requested_by_id=None, force=False, fetch_job_id=None)` |
| Trigger | `enqueue_farm_fetch(farm=..., start=..., end=..., requested_by=..., force=..., countdown=...) -> task_id` — enqueues and returns immediately; performs no HTTP |

Flow: load farm (missing → `farm_not_found`, no job) → resolve point (`POINT_ON_SURFACE` of the
largest boundary part, or the farmer's `location`) → skip if every requested date already has
`AVAILABLE` values (`already_current`, **no HTTP**) → create `DataFetchJob` → POWER client →
`persist_power_response` → return counts.

### Reliability and performance

- **Retries**: only `PowerTransientError`, bounded by `NASA_POWER_TASK_MAX_RETRIES` (2) with exponential
  backoff (`5 s`, `10 s`); permanent `4xx`/malformed/configuration errors fail immediately.
- **One job per scan**: the retry carries `fetch_job_id`, so retries refine the same `DataFetchJob`.
- **Concurrency**: partial unique constraint `uniq_running_job_per_farm` (migration `0003`) allows one
  RUNNING job per farm; a duplicate scan returns `already_running` **without** calling NASA. A RUNNING
  job older than `NASA_FETCH_STALE_JOB_SECONDS` (1800) is retired as `stale_job` and replaced.
- **Timeouts**: task `soft_time_limit=300`, `time_limit=360` (below the global 540/600), plus the client's
  connect/read timeouts.
- **Rate limiting**: `rate_limit=12/m` per worker — no new infrastructure, no parallel burst at POWER.
- **No unnecessary downloads**: default window is 365 days ending 3 days before today; refreshes fetch
  only the contiguous span still missing data.
- **No data corruption**: persistence happens only after a fully validated response; failures only write
  job metadata. Verified by test (rows and values unchanged after a failed refresh).
- **No startup/schedule side effects**: no beat entry, no model signal, nothing fetched at boot.

### Live end-to-end verification (real worker, real Redis, real NASA)

Worker (`--pool=solo`) registered `earth_data.ingest_farm_environment [rate_limit=12/m]`; a queued task for
demo farm 4 (boundary) over 2025-06-01…07 returned `SUCCEEDED` with **49 rows created**, all 7 parameters,
`geometry_source=POINT_ON_SURFACE`, requested `30.998/30.787`; a second identical enqueue returned
`already_current` with **no new job and no new rows**. Worker shut down afterwards.

### Tests

`backend/tests/test_earth_data_tasks.py` — **18 tests**, mocked NASA, no broker: success and counts,
partial success (missing days), `already_current` skip (no HTTP), force refresh updating existing rows,
permanent failure without retry, transient retry scheduling (backoff/kwargs/job stays RUNNING), retry
continuing the same job, exhausted retries → FAILED, **no data loss after a failed refresh**, farm not
found, invalid range, duplicate concurrent scan, stale-job recovery, bounded default window, coordinate
strategy (largest part / farmer point), enqueue helper, and task metadata (name, rate limit, timeouts,
empty beat schedule).

**Full suite:** **143 tests OK** (125 previous + 18 new); `manage.py check` clean;
`makemigrations --check` → no changes.

## Phase 3E Completion — Environmental Data REST API

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Endpoints (all JWT-authenticated, owner-scoped)

| Method | Path | Behaviour |
|---|---|---|
| `POST` | `/api/v1/farms/{farm_id}/scans/` | Validate → plan → create job → enqueue Celery → **`202`** with `job_id`, `task_id`, `status_url`. `200 already_current` when nothing is missing, `409 already_running` when a scan holds the single RUNNING slot, `400` on invalid input, `503` when the broker is unavailable (job marked `FAILED`). |
| `GET` | `/api/v1/data-jobs/{job_id}/` | Application-level job status with timestamps, counts, `error_code`/`error_message` and `status_url`. No tracebacks or raw provider payloads. |
| `GET` | `/api/v1/farms/{farm_id}/environment/daily/` | Paginated (20/page) daily observations with `start`/`end`/`parameter` filters, per-parameter units/product/aggregation metadata, requested vs returned coordinates, grid-cell note, and `MISSING` rows with `value: null`. |

Farm lookups are filtered by `owner=request.user`, so another farmer's farm or job is `404`
(never `403`), and `IsFarmOwner` is applied as defence in depth.

### Validation (bounded requests)

ISO dates; `start <= end`; window ≤ `NASA_FETCH_MAX_RANGE_DAYS` (366); `start >= 1981-01-01`;
`end <= today`; per-parameter first availability (solar `1984-01-01`); parameter codes must be in
the active catalogue; ≤20 parameters. Defaults are the bounded 365-day window ending 3 days before
today, so no request can be unbounded.

### Job status vs Celery state (documented)

Expected provider failures are recorded on the `DataFetchJob` and the task returns a `failed`
summary (Celery state `SUCCESS`). Unexpected internal errors are recorded and then re-raised so
Celery reports `FAILURE` for operators. The job row — not the Celery state — is the source of
truth for data availability.

### Tests

`backend/tests/test_earth_data_api.py` — **31 tests**: authentication on all three endpoints, owner
retrieval, cross-user `404` for observations/scans/jobs, successful retrieval with units and
provenance, date/parameter filtering (comma and repeated), pagination (20/20/9), missing-value
projection, solar metadata, invalid dates/range/future/unknown parameter/pre-1984, `202` refresh
with identifiers, duplicate `409`, `already_current` `200`, `force` refresh, enqueue-failure `503`
with the job marked failed, point-only farm scans, job status fields, and an end-to-end
API → task → persistence → retrieval test with NASA mocked.

**Full suite:** **174 tests OK** (143 previous + 31 new) · `manage.py check` clean ·
`makemigrations --check` → no changes.

## Phase 3 Closeout Review (2026-11-09)

**Status:** ✅ Reviewed · documentation complete · no functional defects outstanding

### Provenance

`DATA_PROVENANCE.md` now records both live retrievals (job ids, timestamps, exact observation counts,
coordinates, units and the seven stored `T2M` values for Run 2), and separates verified evidence from
what was not retained (raw JSON, `times.data`, provider compute time).

### Review findings

| Area | Result |
|---|---|
| NASA client | Pass — verified parameter allow-list, AG/JSON/UTC fixed, `-999` → `null`, `time-standard` asserted, retries bounded, `Retry-After` honoured, no duplicate requests within the cache window |
| Models / constraints | Pass — unique `(farm, source, observation_date)`, value/quality consistency check, coordinate-range checks, GiST-free scalar indexes; catalogue→`PROTECT`, job→`SET_NULL`, farm→`CASCADE` |
| Persistence | Pass — idempotent bulk upsert with explicit timestamps (`bulk_create` skips `auto_now`), counts created vs updated, inactive catalogue rejected before writing, non-`PowerResponse` input rejected |
| Celery task | Pass — one job per scan across retries, transient-only retries with backoff, stale-job recovery, expected provider failures recorded (task `SUCCESS`), unexpected errors recorded then re-raised (task `FAILURE`) |
| Fetch planner | Pass — `POINT_ON_SURFACE` of the largest part, farmer point for location-only farms, missing-day windowing, single shared implementation for task and API |
| Validation / serializers | Pass — ISO dates, ordering, 366-day cap, 1981/1984 availability floors, catalogue-only codes; **defect found and fixed:** the documented ≤20-parameter ceiling was not enforced in `validate_parameters` (unreachable today because the catalogue has 7 codes, but the contract promised it) |
| REST views / routing | Pass — owner-scoped `404`, `202`/`200`/`409`/`400`/`503` semantics verified, no raw payloads, no internal ids except the job UUID |
| Query efficiency | Pass — paginated reads are a constant **8 queries** for 14 or 49 rows (no N+1); an `already_current` scan is 10 queries and one provider-free path |
| Whitespace hygiene | **Fixed** — `git diff --check` flagged trailing whitespace in `API_CONTRACTS.md`; corrected |
| Decimal strings | Confirmed intentional; frontend conversion (`Number(value)` after a `null` check) documented in the contract |

### Open items (documented, not implemented)

- **Throttling**: `POST /scans/` has no DRF throttle. Acceptable for the private dev environment given
  the one-running-job constraint and Celery `12/m` rate limit; a **pre-public-deployment requirement**
  (recommended ~10 scans/hour and 60 reads/minute per user).
- `GET /environment/daily/` reports one `spatial` block describing the most recent fetch; per-row
  coordinates are stored but not exposed. Add per-row coordinates only if the UI needs mixed-provenance
  ranges.
- Deactivating a catalogue row makes its historical observations unqueryable through the API (validation
  accepts active codes only). Intentional, but worth revisiting before Phase 4.
- `DataJobDetailView` filters on `provider=NASA_POWER`; a second provider would need that filter relaxed.

## Phase 3F — Complete Integration Verification (QA)

**Status:** ✅ PASSED (2026-11-09). No new features were added; no defects required correction.

### Workflow verification (real worker, real NASA, real database)

| Step | Evidence |
|---|---|
| Farm exists | Farm 4 "Demo - North Field (Gharbia)", boundary `MultiPolygon`; farm 5 point-only |
| Representative coordinates | `POINT_ON_SURFACE` → 30.998/30.787, verified `boundary.contains(point) == True`; farm 5 uses the registered farmer point exactly |
| Correct NASA request | Built URL carries `parameters=…`, `community=AG`, `format=JSON`, `time-standard=UTC`, `YYYYMMDD` dates |
| Response validated | Parser asserts echoed time standard, per-parameter units, coordinate echo; `-999`/null → MISSING |
| Observations persisted | 147 rows across 5 jobs, all `SUCCEEDED` |
| Codes/units/provenance preserved | REST read-back shows `T2M` in `C` from `MERRA-2` with requested vs returned coordinates |
| Repeated fetches do not duplicate | `duplicate (farm, param, date)` count = **0**; August window = 49 rows after two overlapping scans |
| Celery executes | worker ping OK, `core.ping` → `pong`, task registered at `12/m`, scan → `SUCCEEDED` in ~2 s |
| REST returns correct data | `GET /environment/daily/?…&parameter=T2M` → 7 August rows, `AVAILABLE`, values in °C |
| Cross-user 404 | Farmer B: observations `404`, scan `404`, job `404`; unauthenticated `401` |

### Live smoke test (Phase 3F)

`POST /farms/4/scans/` for 2025-08-01→07 (7 parameters) → **202** → job `SUCCEEDED`,
`days_stored=7`, `days_missing=0` → 49 rows stored → August `T2M` read back via REST:
29.45 / 29.57 / 29.79 / 29.44 / 29.16 / 29.37 / 28.45 °C. A second force-scan of the same window
enqueued cleanly and updated the same rows in place (no duplicates). QA accounts were removed
afterwards; demo data untouched.

### Full verification results

`manage.py check` clean · `makemigrations --check` no changes · Compose config valid ·
backend **175/175 OK** (Phase 1: 13, Phase 2: 63, Phase 3: 99) · frontend **53/53 OK** (untouched) ·
`git diff --check` clean · no destructive migration operations in `earth_data.0001–0003` ·
Postgres/Redis containers and the `postgres_data` volume intact (3 days uptime) ·
Phase 1/2 data intact (users 2, profiles 2, farms 2, contexts 1, crops 2) · no secrets in changes ·
branch `phase/3-nasa-integration` with no Git operations performed.

## Phase 4B Completion — Indicator Foundation (Water + Heat)

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Decisions recorded

ADR-021 (demo region `EG-GH`), ADR-022 (indicator contract, `score: null`, coverage/freshness rules,
no snapshot model), ADR-023 (water/heat/soil/market methodology). Region code fits the existing
`Farm.region_code` field (max_length 80) — no schema change.

### Application foundation (`apps/indicators/`)

| Module | Contents |
|---|---|
| `contract.py` | `IndicatorStatus` (OK / PARTIAL / INSUFFICIENT_DATA / NOT_ASSESSED / UNAVAILABLE), `Confidence` (NONE / LOW / MEDIUM / HIGH), `Freshness` (FRESH / RECENT / STALE / UNKNOWN), `Coverage`, `Period`, `Measurement`, `SourceReference`, `MissingInput`, `Driver`, `Methodology`, `IndicatorResult` (uniform envelope, `score` always `null`, JSON-safe `as_dict()` with decimals as strings) |
| `coverage.py` | Non-overlapping confidence bands (0 / <60 / <95 / ≥95 %), grid-cell confidence cap (MEDIUM), freshness bands (≤7 d / ≤30 d / stale), inclusive window helpers, `latest_window()` (window ends at the newest observation), coverage math |
| `services/water.py` | `PRECTOTCORR`: total over covered days, rainy days ≥ 1.0 mm (configurable), max daily rainfall, longest observed dry run with contiguity flag, coverage, status, confidence, provenance, farmer-reported irrigation as context |
| `services/heat.py` | `T2M` / `T2M_MAX` / `T2M_MIN`: mean, mean max, mean min, hot days ≥ 35 °C, very hot ≥ 40 °C, cool nights ≤ 5 °C (all configurable), per-parameter coverage, headline coverage = weakest parameter |
| `selectors.py` | DB adapters over Phase 3 tables (`parameter_series`, `observed_dates`, `source_reference(s)`) — services stay pure and never call NASA |

**Settings** (all configurable): `INDICATOR_DEFAULT_WINDOW_DAYS=30`, `INDICATOR_MAX_WINDOW_DAYS=366`,
`INDICATOR_RAINY_DAY_MM=1.0`, `INDICATOR_HOT_DAY_C=35`, `INDICATOR_VERY_HOT_DAY_C=40`,
`INDICATOR_COOL_NIGHT_C=5`, `INDICATOR_FRESH_MAX_DAYS=7`, `INDICATOR_RECENT_MAX_DAYS=30`,
`INDICATOR_SOIL_FRESH_MONTHS=12`, `INDICATOR_SOIL_STALE_MONTHS=24`.

### Methodology guards implemented

- Missing days never become zero rainfall/temperature/exposure; totals and counts cover observed days only.
- A dry spell is only contiguous when the window has no gaps; otherwise the longest **observed** run is
  reported with an explicit limitation.
- Counts are `null` (not `0`) when a parameter has no observation at all.
- Confidence is capped at MEDIUM for grid-cell sources; freshness is reported separately.
- No numeric scores; no soil/market implementation; no snapshots, migrations, endpoints or frontend.

### Tests

| File | Tests |
|---|---|
| `test_indicator_contract.py` | 16 |
| `test_indicator_water.py` | 14 |
| `test_indicator_heat.py` | 15 |
| `test_indicator_selectors.py` | 10 |

Covers known totals, rainy days, contiguous and gap-interrupted dry spells, means, all three exposure
counts, missing values, empty windows, coverage bands, confidence caps, freshness/stale data, source
provenance, Decimal-safe output, and services reading real Phase 3 rows.

**Full suite:** **230 tests OK** (175 previous + 55 new); `manage.py check` clean;
`makemigrations --check` → no changes (no models added).

## Phase 4C Completion — Soil and Market Indicators

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Soil (`apps/indicators/services/soil.py`)

Per-property reporting from `FarmerContext`; **no composite score**.

| Property | Unit | Interpretation |
|---|---|---|
| `ph` | pH | descriptive band only: `ACIDIC < 6.0`, `NEUTRAL 6.0–7.5`, `ALKALINE > 7.5` |
| `organic_carbon_percent` | % | reported as measured; no good/bad threshold, no trend from one sample |
| `nitrogen_ppm` / `phosphorus_ppm` / `potassium_ppm` | ppm | method preserved; **never** classified deficient/sufficient/excessive |
| `texture_class` | class | qualitative context; no water-holding capacity derived |

Sampling metadata (`sample_date`, `sampling_depth_cm`, `sampling_method`, `lab_name`) is returned in
`context`; provenance (`soil_source`) is carried on every measurement.

**Sample freshness** (operational labels, separate from confidence): `FRESH < 12 months`,
`AGEING 12–24`, `STALE > 24`, `UNKNOWN` when no date, and **`FUTURE`** for a future date (never treated
as fresh). Thresholds configurable via `INDICATOR_SOIL_FRESH_MONTHS` / `INDICATOR_SOIL_STALE_MONTHS`.

**Status/completeness:** `OK` when all six core properties exist, `PARTIAL` when some do (with an
explicit `missing[]` list), `INSUFFICIENT_DATA` when there is no context or no soil property.
`coverage` is `null` (no daily window); a new `completeness` block reports properties expected/present.

**Confidence** = completeness × provenance factor (LAB_TEST 1.0, EXTERNAL_PROVIDER 0.8,
FARMER_REPORTED 0.7, REMOTE_SENSING 0.6, UNKNOWN 0.4) × freshness factor (FRESH 1.0, AGEING 0.75,
STALE 0.5, UNKNOWN 0.6, FUTURE 0.4), mapped to the shared bands. Example: complete fresh lab sample →
HIGH; complete fresh farmer-reported → MEDIUM; complete stale lab → LOW.

### Market (`apps/indicators/services/market.py`)

Always `status: UNAVAILABLE`, `confidence: NONE`, `score: null`, **no measurements and no prices**.
The summary names the farm's region; `missing[]` lists local prices, crop-specific price, market access
and expected yield; `limitations[]` documents the verified national sources (FAOSTAT producer prices,
WFP retail) as **context only**, explicitly not local farm-gate prices, and states that no synthetic or
demo prices are used (R18).

### Contract additions (additive, no behaviour change for water/heat)

`Freshness.AGEING` / `Freshness.FUTURE`; `Measurement.value` may be text (texture) and carries an
optional `interpretation`; `Coverage` is optional; new `Completeness` block for non-time-series
indicators.

### Tests

| File | Tests |
|---|---|
| `test_indicator_soil.py` | 19 |
| `test_indicator_market.py` | 8 |
| `test_indicator_selectors.py` (extended) | 13 (was 10) |

Covers pH bands and boundaries, organic carbon without thresholds, N/P/K method preservation and no
classification, texture as context, all freshness labels including future dates, partial profiles with
missing lists, absent context, provenance-driven confidence, stale samples, no composite score, market
unavailability, and soil indicators built from a real `FarmerContext`.

**Full suite:** **260 tests OK** (230 previous + 30 new); `manage.py check` clean;
`makemigrations --check` → no changes (still no models).

## Phase 4D Completion — Environmental Summary API

**Status:** ✅ COMPLETE (2026-11-09), uncommitted

### Endpoint

`GET /api/v1/farms/{farm_id}/environment/current/?window_days=30`

- JWT required; farm resolved with `owner=request.user` → another farmer's farm or unknown id `404`,
  anonymous `401`; the owner always gets `200`.
- `window_days` default 30, range 1–366; invalid/out-of-range → `400` with a `window_days` error.
- Returns `farm_id`, `generated_at`, `window`, `data_status`, `freshness`, `indicators`
  (`water`, `heat`, `soil`, `market`) and top-level `limitations`.
- Every indicator uses the shared envelope (`code, label, status, score, confidence, as_of, period,
  coverage, completeness, summary, measurements, context, drivers, missing, methodology, sources,
  limitations`); `score` is `null` everywhere; `market` is always `UNAVAILABLE`.

### "Current" means latest available observation

The window ends at the **latest stored observation** (not today) and spans `window_days` back.
`window.latest_observation`, `window.age_days` and `window.freshness` expose staleness; with no
observations the window ends today and the time-series indicators report `INSUFFICIENT_DATA`.
Soil uses its sample date and market has no observation period, so neither receives the climate window.

### Top-level `data_status`

| Condition | Status |
|---|---|
| water, heat and soil all `OK` | `OK` |
| at least one of them `OK`/`PARTIAL` | `PARTIAL` |
| none assessable | `INSUFFICIENT_DATA` |

`MARKET` is excluded from this roll-up because it is `UNAVAILABLE` by design (R18) — it must not make
the whole response look unavailable.

### Orchestration and performance

`apps/indicators/summary.py` builds the response; the view only resolves the farm, validates
`window_days` and calls the orchestrator. One shared window query serves water and heat (no per-day or
per-parameter queries), and the catalogue/context are fetched once:

| Query | Purpose |
|---|---|
| 1 | owner-filtered farm lookup |
| 2 | latest observation date (aggregate) |
| 3 | all seven parameters for the window (single query) |
| 4 | dataset source metadata (single query) |
| 5 | farmer context (single query) |
| 6 | (test client) — total asserted as **6** |

`source_references()` was rewritten from one query per parameter to a single query (verified
performance defect fixed during integration).

### Tests

`backend/tests/test_indicator_summary_api.py` — **26 tests**: anonymous 401, other farmer 404,
nonexistent 404, owner 200 without data, default/custom/min/max windows, invalid windows (0, −5, 367,
1000, `abc`, `1.5`), all four indicators present with the full envelope, market always `UNAVAILABLE`,
no numeric scores, `as_of` per indicator, soil not given the climate window, irrigation context,
no real-time claims, no-observations status, soil-only partial, sparse coverage, complete-window `OK`,
missing/partial soil, stale freshness and age-days, latest-observation date, and a **6-query**
assertion.

**Full suite:** **286 tests OK** (260 previous + 26 new); `manage.py check` clean;
`makemigrations --check` → no changes (no models added).

## Phase 4E Completion — Documentation, Methodology and Provenance

**Status:** ✅ COMPLETE (2026-11-12), uncommitted

### New document

[`ENVIRONMENTAL_INDICATORS.md`](ENVIRONMENTAL_INDICATORS.md) — the authoritative description of the
four indicators: shared contract, status/confidence/freshness rules, "current = latest available
observation", per-indicator formulas and units, configurable thresholds, provenance summary, known
limitations and verified references.

### Methodology identifiers (as implemented)

| Indicator | Identifier | Version |
|---|---|---|
| Water | `water.rainfall.v1` | 1.0.0 |
| Heat | `heat.exposure.v1` | 1.0.0 |
| Soil | `soil.properties.v1` | 1.0.0 |
| Market | `market.unavailable.v1` | 1.0.0 |

The Phase 4A prompt suggested `soil.profile.v1` as an example; the implemented identifier is
`soil.properties.v1` and the documentation records the code, not the example.

### Provenance

`DATA_PROVENANCE.md` gained §11 "Derived Indicators (Phase 4)": indicator → methodology → inputs,
a source-type distinction (provider observation / farmer-reported / laboratory / derived /
unavailable), an explicit list of what is deliberately **not** derived (soil moisture, ET, water
stress, crop heat stress, market prices, climate normals), and a pointer to the threshold table.

### API contract

`API_CONTRACTS.md` §4 now documents the exact endpoint, JWT/ownership behaviour, `window_days`
(default 30, 1–366), the latest-observation anchoring, top-level `data_status` rules, all four
indicator structures, status/confidence/freshness values, missing-data behaviour, market
`UNAVAILABLE`, HTTP codes, and a **real serializer example** (captured from the development demo farm,
not hand-written).

### Consistency pass

- `README.md`: added the Phase 4 section (endpoint, indicator summary, docs links) and corrected the
  stale "not implemented" list and frontend test count (53).
- `DEVELOPMENT_PLAN.md`: 4A–4E marked complete.
- `ARCHITECTURE_DECISIONS.md`: added ADR-024 ("current" = latest available observation).
- No documentation claims a feature that does not exist; no invented thresholds, prices or citations.

### Verification

`git diff --check` clean · documentation links resolve to existing files · methodology ids, parameter
codes and units cross-checked against `apps/indicators/` and the `DatasetSource` catalogue · API
example parsed as JSON and compared field-by-field with a live response · no secrets in any changed
file · indicator tests re-run: **111 tests OK** (contract 16, water 14, heat 15, soil 19, market 8,
selectors 13, summary API 26).

## Phase 4F Completion — NASA Data-Source Documentation Alignment

**Status:** ✅ COMPLETE (2026-11-13), uncommitted, documentation only + one test correction

### What was wrong before this pass

The documentation implied or stated more integration than existed. `DATA_PROVENANCE.md` still called GPM
IMERG and SMAP "MVP Candidate" / "P1 scope", the soil section described SoilGrids as an active fallback,
and `API_CONTRACTS.md` showed a fabricated `period` object for MARKET. The repository audit confirmed
that **only NASA POWER** has a provider adapter, catalogue rows, stored observations and verified
API read-back.

### New document

[`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md) — the canonical record of the
NASA Space Apps 2026 datasets: product/version, coverage, spatial and temporal
resolution, variables and units, intended agricultural use, quality/missing-data limitations, official
access method, integration status, phase, and why U.S.-only resources cannot serve Gharbia. It also
carries the spatial reality check, the architecture gaps that block raster sources, and the explicit
"do not integrate" decisions.

### Integration classification (verified)

| Class | Datasets |
|---|---|
| **Integrated** | NASA POWER only (WATER + HEAT inputs) |
| **Evaluated, not integrated — Phase 5 candidate** | GPM IMERG, SMAP, Landsat C2, Sentinel-2, HLS, MODIS/VIIRS, ECOSTRESS, GAEZ v5 |
| **Evaluated, not integrated — later phase** | SRTM, GLDAS-2.1, ERA5/ERA5-Land |
| **Not suitable for annual-crop monitoring** | GEDI |
| **Not suitable for Gharbia (U.S.-only)** | WSS, SSURGO/STATSGO2, CDL, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS Market News, NASS QuickStats, OpenET, LANDFIRE |
| **Requires dataset-by-dataset validation** | USDA Ag Data Commons (a repository, not a dataset) |

### Documentation changes

- `DATA_PROVENANCE.md`: status header, integration note, implemented POWER processing steps, IMERG/SMAP/
  ECOSTRESS reclassified as evaluated-not-integrated with verified product details, SoilGrids no longer
  presented as an active fallback, evaluated-dataset table rewritten, matrix reference added.
- `API_CONTRACTS.md`: Phase 4 source scope, nullable `as_of`/`period` rule, MARKET `period` example
  corrected to `null` (it previously showed a window that the code never returns).
- `ENVIRONMENTAL_INDICATORS.md`: source scope, nullable `period` row, top-level vs indicator-level
  freshness caveat, matrix pointer.
- `README.md`: integrated-data-source note and matrix link.
- `DEVELOPMENT_PLAN.md`: Phase 4F slice and corrected Phase 5 priorities.
- `PROJECT_STATUS.md`: this section plus corrected branch, test-count and documentation-inventory claims.

### Methodology preserved

WATER and HEAT calculations, thresholds and units are unchanged. SOIL still reports `FarmerContext`
measurements with provenance and no composite score. MARKET remains `UNAVAILABLE`. All scores remain
`null`. No synthetic soil value, market price or rainfall value was introduced. Confidence and freshness
remain separate. The matrix records the interpretation rules that must survive future integration:
SMAP moisture ≠ laboratory soil measurement, ECOSTRESS LST ≠ air temperature, GPM rainfall ≠
irrigation-water availability, NDVI/EVI ≠ soil health, GAEZ suitability ≠ field-specific yield guarantee.

### Test correction (disclosed)

`tests/test_indicator_soil.py::SoilFreshnessTests::test_missing_sample_date_is_unknown` asserted a
`Period` object for a soil profile with no sample date, but `calculate_soil_indicator()` intentionally
returns `period=None` in that case (documented in `API_CONTRACTS.md`). The test was updated to assert
`period is None`, `freshness=UNKNOWN` via the driver, and the "sample date not recorded" summary. **No
application code, model, migration, endpoint, task or calculation was changed in Phase 4F.**

### Verification

`manage.py check` clean · `makemigrations --check` no changes · full backend suite **286 tests OK** ·
soil module **19 tests OK** · frontend **53 tests OK** · `npm run lint` and `npm run build` clean ·
`git diff --check` clean · documentation links resolve to existing files · no secrets in changed files.

> **Not verified in this pass:** live acquisition counts over Gharbia for ECOSTRESS, GEDI, Landsat or
> Sentinel-2; seasonal cloud statistics; Egyptian farm-size distribution; complete licence terms; exact
> current versions of every SMAP L4/ECOSTRESS product. These need a read-only Phase 5 validation spike.

## Phase 5.3 — Crop Rotation Evidence Engine (implementation in this checkout)

- Added a pure deterministic evidence-readiness evaluator. It distinguishes missing history,
  ambiguous history, missing crop codes, missing regional calendars/profiles, incomplete
  environmental provenance, stale NASA inputs, and unsupported/unreferenced constraints.
- A farmer-history baseline is shown only when the exact requested horizon is present and
  is explicitly labeled as past farmer-provided history, not a future recommendation.
- Candidate options require sourced calendar dates/evidence, eligible regional profiles and
  evidence-linked traits. Hard exclusions are honored only for approved, source- and
  evidence-backed supported rule types. Unsupported constraints are reported, not applied.
- No numeric scores, arbitrary weighted ranking, yield/profit estimates, or promised soil
  outcomes. Current catalogue/calendar emptiness yields empty alternatives and explicit
  `INSUFFICIENT_EVIDENCE`.
- Added owner-scoped routes generate, retrieve, compare, and return explanation/provenance.
  Inputs, recent stored environmental evidence, crop-history/context snapshot, engine version,
  and SHA-256 are persisted.
- Added migration `0004_sync_phase5_models` to align the Phase 5 models with the migrations.
  It is additive and no historical migration was edited.
- Verification (2026-11-14, Docker/PostGIS runtime): `python manage.py test tests` →
  **325 tests OK**; `manage.py check` clean; `makemigrations --check --dry-run` → no changes.
  Frontend: **61 tests OK**, `oxlint` clean, production build succeeded.
- Known gap closed: candidate selection now requires `approval_status = APPROVED` and
  reviewer-decided geographic applicability; a source's `VALID` claim alone is never
  region-ready. See [`PHASE_5_STATUS.md`](PHASE_5_STATUS.md) §4.

## Open Decisions and Dependencies

| Decision | Status | Owner |
|---|---|---|
| Demonstration region and stable `region_code` | ✅ Resolved 2026-11-09: Gharbia, Egypt — `EG-GH` (ADR-021) | Team |
| Farmer persona, farm scale, crop system, seasons/calendar | Needs team decision | Team + Person C |
| Minimum regional crop catalog / expert reviewer | Source/reviewer not selected | Person C |
| Authentication identity | ✅ Resolved: `username` login on Django's built-in user + `FarmerProfile` (ADR-019) | Team + Person A |
| Map library | ✅ Resolved 2026-11-07: Leaflet + Leaflet-Geoman Free with React Leaflet (ADR-017) | Person B |
| NASA POWER parameters for demo region | ✅ Resolved 2026-11-09: `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN` | Person A + Person C |
| Second precipitation source (GPM IMERG) | Open: requires an approved observation-schema extension before implementation (matrix §8) | Team |
| Egyptian farm-gate market prices | Open: no verified local source; MARKET stays `UNAVAILABLE` (R18) | Team + Person C |
| Deployment target | Needs team decision | Team |

## Corrected Scope Decisions

- NASA POWER is the only integrated source; it is reanalysis/assimilation, not on-farm measurement.
- Farm boundaries planned as SRID 4326 geometry; geodesic area via geography cast (Phase 2).
- Strategy enum: `BASELINE`, `WATER_EFFICIENT`, `SOIL_REGENERATION`.
- GPM IMERG, SMAP, Landsat/Sentinel-2/HLS, MODIS/VIIRS, ECOSTRESS, GAEZ, SRTM, GLDAS and ERA5 are
  **evaluated but not integrated**; see [`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md).
  Report export and the optional 80% gate remain P1/deferred.
- U.S.-only resources (WSS, SSURGO, CDL, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS/QuickStats,
  OpenET, LANDFIRE) are out of scope for Gharbia and must not be used as demo or fallback data.

## Git Workflow Status

- Phase 2 published (`f1657fe`, `36a4e81`, `d9cf020`) and merged into `develop` (`c4a03a6`).
- Phase 3 published on `phase/3-nasa-integration`: `0f9ee8f` (client + models), `3f6a1ee` (persistence + Celery),
  `d2fdcb8` (REST API), `063c776` (provenance/contracts/QA docs).
- Phase 3 merged into `develop` with `--no-ff` (`37db0b3`) and pushed.
- `phase/4-environmental-engine` created from the merged `develop` and published.
- Phase 5 (`crop-intelligence-rotation-engine`) committed and published to the `overfield`
  remote as `phase/5-rotation-engine`; `origin` remains at the Phase 4 baseline by design.
- `phase/6-simulation` created from the Phase 5 tip with a Phase 6 slice plan; no Phase 6
  feature code is included.
- `main` is still at the Phase 0 baseline (`d59156b`). Promote `develop` → `main` once the team approves
  Phases 1–3 (optionally tagged `phase-3-approved`); nothing is forced or rewritten.
- No milestone tags created yet.

## Next recommended task

1. **Complete the release activities in the Phase 4 audit.** The verdict is
   **CONDITIONAL**: `docs/PHASE_4_RELEASE_AUDIT.md` records the evidence and the three
   remaining release activities (live browser E2E, live NASA staging scan, bundle
   optimisation) plus the expired-token test gap.
2. **Source and review the Gharbia crop catalogue and calendar** (Risk R6/R13). No crop trait
   or season window may be entered without a named, approved dataset and reviewer.
3. **Phase 6 — Scenario Simulation and Strategy Comparison.** Scenarios must be explicit,
   bounded and reproducible; hypothetical adjustments must never be labelled as NASA
   forecast. See `DEVELOPMENT_PLAN.md` and the branch `phase/6-simulation`.
4. **Keep production rotation fail-closed.** Until reviewed crop evidence exists, the API
   must keep returning `INSUFFICIENT_EVIDENCE` with named missing inputs; this is asserted
   by tests, not a placeholder.

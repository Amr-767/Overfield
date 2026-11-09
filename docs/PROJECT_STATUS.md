# AgroSpace Quest — Project Status

**Last updated:** 2026-11-07
**Current phase:** Phase 3 — NASA Data Providers and Asynchronous Ingestion
**Phase status:** ✅ Phase 3 COMPLETE, reviewed and QA-verified (3A–3F) · 175 backend + 53 frontend tests · uncommitted

> The Phase 1 foundation is complete and integration-verified. **Phase 2 Step 0** moved Django into the Compose stack so GeoDjango runs with native GDAL/GEOS/PROJ (ADR-018), enabled the PostGIS backend, verified the spatial stack end to end, and recorded the Leaflet + Leaflet-Geoman mapping decision (ADR-017). **Phase 2 backend** added the account profile, JWT endpoints, `Farm`/`FarmZone`/`FarmerContext`/`FarmCropHistory` models, owner-scoped APIs, geodesic area calculation and 63 tests. **Phase 2 frontend** added the five-step farm onboarding wizard with a Leaflet + Geoman boundary editor, auth screens, farm list/detail pages, and 44 new frontend tests. Nothing is committed yet; no Phase 3 work has started.

## Repository Audit (current checkout)

| Item | Actual status |
|---|---|
| Repository | Git repository initialized; current branch is `phase/2-farm-management` |
| Local branches | `main`, `develop`, `phase/0-documentation-review`, `phase/1-foundation`, `phase/2-farm-management` |
| Remote | `origin` configured to `https://github.com/Amr-767/nasa.git`; all five branches published and tracking their origin counterparts |
| Backend (`backend/`) | Django 6.0.10 + GeoDjango (`django.contrib.gis`) with the PostGIS backend; `config/` split settings, DRF + SimpleJWT, CORS, `apps.core` (health), `apps.accounts` (profile/auth), `apps.farms` (farms/zones/context), `domain_services` (geometry). Runs in the `backend` Compose service (ADR-018) |
| Frontend (`frontend/`) | React 19 + TypeScript + Vite + React Router 7 + TanStack Query 5 + Leaflet 1.9/Leaflet-Geoman: auth screens, 5-step onboarding wizard, farm list/detail, env-driven API client with JWT handling |
| Documentation (`docs/`) | Master Handoff, Phased Coding Playbook, Phase 0 docs, Git workflow, review, and risk register present |
| `README.md` | Documents Phase 1A infrastructure, Phase 1B backend, and Phase 1C frontend setup/run/build/lint/test commands |
| `.gitignore` | Present; `.env` and `.venv/` ignored |
| `.env.example` | Present with Postgres/Redis/Django placeholders; local `.env` is ignored |
| Dependencies | Backend pinned in `backend/requirements.txt` (adds `celery[redis]` in Phase 1D); frontend pinned in `frontend/package.json` + `package-lock.json`; virtualenv and `node_modules` are local-only |
| Tests | Backend: **76 Django tests** (63 Phase 2 + 13 Phase 1) passing. Frontend: **53 Vitest tests** (7 Phase 1 + 46 Phase 2) passing |
| Frontend deps | `react-router-dom`, `@tanstack/react-query`, `leaflet`, `react-leaflet`, `@geoman-io/leaflet-geoman-free`; test-only `jsdom`, `@testing-library/react`, `@testing-library/user-event` |
| Database | Docker Compose `postgis/postgis:17-3.5` (PostgreSQL 17.5, PostGIS 3.5.2); Django uses `django.contrib.gis.db.backends.postgis` |
| Backend runtime | Docker image `python:3.14-slim` (Debian 13) with GDAL 3.10.3, GEOS 3.13.1, PROJ 9.6.0; `backend/Dockerfile` + `backend/.dockerignore`; the host venv is editor-only |
| Redis | Local Docker Compose: `redis:7.4.12`; used by Celery (Phase 1D) as broker (DB 0) and result backend (DB 1) |

### Documentation inventory

- [`AgroSpace_Quest_Master_Agent_Handoff.md`](AgroSpace_Quest_Master_Agent_Handoff.md) — primary product/specification source
- [`AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md`](AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md) — phased execution guide
- [`AgroSpace_Quest_Phase0_Review.md`](AgroSpace_Quest_Phase0_Review.md)
- [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)
- [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md)
- [`API_CONTRACTS.md`](API_CONTRACTS.md)
- [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md)
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

## Open Decisions and Dependencies

| Decision | Status | Owner |
|---|---|---|
| Demonstration region and stable `region_code` | Needs team decision | Team |
| Farmer persona, farm scale, crop system, seasons/calendar | Needs team decision | Team + Person C |
| Minimum regional crop catalog / expert reviewer | Source/reviewer not selected | Person C |
| Authentication identity | ✅ Resolved: `username` login on Django's built-in user + `FarmerProfile` (ADR-019) | Team + Person A |
| Map library | ✅ Resolved 2026-11-07: Leaflet + Leaflet-Geoman Free with React Leaflet (ADR-017) | Person B |
| NASA POWER parameters for demo region | Verify before Phase 3 | Person A + Person C |
| Deployment target | Needs team decision | Team |

## Corrected Scope Decisions

- NASA POWER is the first planned integration; meteorological parameters are reanalysis/assimilation estimates where applicable.
- Farm boundaries planned as SRID 4326 geometry; geodesic area via geography cast (Phase 2).
- Strategy enum: `BASELINE`, `WATER_EFFICIENT`, `SOIL_REGENERATION`.
- GPM, report export, and optional 80% gate remain P1/deferred.

## Git Workflow Status

- Phase 2 published on `phase/2-farm-management`: `f1657fe` (backend), `36a4e81` (frontend), `d9cf020` (docs).
- Phase 2 merged into `develop` with `--no-ff` (`c4a03a6`) and pushed to `origin/develop`.
- `phase/3-nasa-integration` created from the merged `develop` and pushed.
- Current branch: `phase/3-nasa-integration`. Phase 3A–3E work is in the working tree and **not yet committed**.
- `main` is still at the Phase 0 baseline (`d59156b`). Promote `develop` → `main` once Phase 1+2 are formally
  approved (optionally with `phase-2-approved` tags); nothing is forced or rewritten.
- No milestone tags created yet.

## Next recommended task

**Review and commit Phase 3** (`phase/3-nasa-integration` → `develop` with `--no-ff`), then start
Phase 4 (environmental indicators and data fusion). `DATA_PROVENANCE.md` still needs the live-retrieval
entry from the Phase 3D worker check.

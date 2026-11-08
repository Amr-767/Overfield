# AgroSpace Quest — Project Status

**Last updated:** 2026-11-07
**Current phase:** Phase 2 — ✅ **COMPLETE** (integration-audited end to end), pending commit/merge
**Phase status:** ✅ ACCEPTED — browser E2E 26/26, geospatial 14/14, permissions 12/12, 76 backend + 53 frontend tests, production build OK

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

- Current branch: `phase/2-farm-management`, tracking `origin/phase/2-farm-management`.
- Phase 2 Step 0 changes (Dockerfile, Compose service, GeoDjango settings, docs) are in the working tree and **not yet committed** — pending review.
- Phase 2 backend implementation (accounts, farms, domain services, tests, migrations, docs) is also **uncommitted**; migrations are applied to the local database only.
- Phase 2 frontend (onboarding, auth screens, farm list/detail, map, tests) is **uncommitted**.
- Phase 1 commits (`ad00e60` scaffold, `7441a43` docs) published on `origin/phase/1-foundation`.
- Phase 1 merged into `develop` via `25855ef` (`merge(phase-1): integrate foundation into develop`) and pushed.
- `phase/2-farm-management` created from latest `develop` and pushed.
- `main` still at the Phase 0 baseline (`d59156b`); update it after the Phase 1 milestone is formally tagged.
- No milestone tags created yet.

## Next recommended task

**Commit Phase 2 and merge `phase/2-farm-management` into `develop`** per `docs/GIT_WORKFLOW.md`,
then obtain team review. Phase 3 (NASA data providers) must not start until that merge is approved.

# AgroSpace Quest — Architecture Decision Records

**Last updated:** 2026-11-05 (ADR-014 and ADR-015 added with Phase 1B)

---

## ADR-001: Modular Monolith Architecture

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The team has 3 members and hackathon time constraints. Microservices add deployment complexity, inter-service communication, and operational overhead.

**Decision:** Build a modular monolith. Django is the single backend process. Domain separation is achieved through Django apps and Python service modules, not separate deployable services.

**Consequences:**
- Simpler deployment (one Django process + Celery workers)
- Shared database with clear model ownership per app
- Service modules can be extracted to separate services later if needed
- All team members work in one repository

---

## ADR-002: Django REST Framework for API Layer

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The frontend (React) communicates with the backend via JSON APIs. Django provides ORM, authentication, and admin. DRF adds serializers, viewsets, permissions, pagination, and throttling.

**Decision:** Use Django + DRF as the API framework. All endpoints are prefixed with `/api/v1/`.

**Consequences:**
- Clean API contract for frontend integration
- Built-in validation and permission patterns
- API versioning ready for future evolution
- Team can use DRF browsable API during development

---

## ADR-003: PostgreSQL + PostGIS for Database

**Status:** Accepted  
**Date:** 2026-11-05 (geometry storage choice clarified)

**Context:** The application requires storing farm boundaries as polygons, calculating geodesic areas, performing spatial queries (which grid cells intersect a farm), and supporting spatial indexes. SQLite cannot do this.

**Decision:** Use PostgreSQL with PostGIS. Store farm boundaries as GeoDjango `MultiPolygonField(srid=4326)` geometry by default. Perform overlay, intersection, clipping, and future raster/vector workflows in geometry with explicit CRS/units and suitable projections. For geodesic area/distance, cast the stored geometry to geography (or use an explicitly selected equal-area/local projected CRS when appropriate); never calculate metric area directly from longitude/latitude degrees. Keep API interchange as GeoJSON in WGS84. Revisit storage type only if the required operation set is confirmed and measured.

**Consequences:**
- Broad PostGIS geometry operation support for likely overlays and spatial processing
- Geodesic area/distance remain available by geography cast without making geography the universal storage type
- Spatial indexing for efficient polygon queries
- All team members need PostgreSQL + PostGIS installed locally
- More complex local setup than SQLite (documented in README)

---

## ADR-004: Celery + Redis for Background Processing

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** NASA API requests can be slow (seconds to minutes). ECOSTRESS/AppEEARS workflows can take minutes to hours. The frontend must not wait synchronously.

**Decision:** Use Celery with Redis as the message broker. NASA data fetching, raster processing, report generation, and scheduled refreshes run as Celery tasks. The API returns HTTP 202 with a job ID for slow operations.

**Consequences:**
- Responsive frontend — user sees "scan in progress" immediately
- Worker failures don't crash the web server
- Redis also serves as short-lived application cache
- Adds local development dependency (Redis process)

---

## ADR-005: React with Vite for Frontend

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The UI requires interactive maps, form-heavy onboarding, chart/gauge visualizations, and a scenario comparison timeline. React provides component reuse and a large ecosystem.

**Decision:** Use React with Vite as the build tool. State management via React hooks and TanStack Query (React Query) for API state.

**Consequences:**
- Fast development with hot module replacement
- Rich mapping library support (Leaflet/MapLibre)
- TanStack Query handles loading/error states and caching
- Frontend and backend can be developed in parallel against API contracts

---

## ADR-006: Four-Layer Backend Architecture

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The spec defines four backend layers. Mixing NASA API calls, business rules, and HTTP handling in one place creates untestable code.

**Decision:** Separate into four layers:

| Layer | Components |
|---|---|
| **Application** | DRF views, serializers, permissions, authentication |
| **Domain** | Farm services, crop catalog, rotation engine, scenario engine, score engine |
| **Data Integration** | NASA POWER, GPM, SMAP, ECOSTRESS adapters and normalizer |
| **Infrastructure** | PostgreSQL/PostGIS, Redis, Celery, object storage, logging |

Business rules live in `domain_services/` modules, not in serializers or views.

**Consequences:**
- Rotation engine can be unit-tested without HTTP or database
- Provider adapters can be swapped or mocked independently
- Clear separation of concerns for team collaboration

---

## ADR-007: Provider Adapter Pattern for External Data

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The application integrates with multiple external data sources (NASA POWER, GPM, SMAP, ECOSTRESS, SoilGrids, etc.). Each has different APIs, authentication, data formats, units, and quality flags.

**Decision:** Use a provider adapter interface. Each adapter implements `fetch()` and `normalize()`. The domain layer consumes normalized `EnvironmentalObservation` records and never directly calls external APIs.

**Consequences:**
- Adding a new data source means writing one adapter, not modifying the rotation engine
- Normalized observations have consistent schema regardless of source
- Provider-specific parsing is isolated and testable
- Adapters can be mocked for deterministic testing

---

## ADR-008: Django App Structure — Domain-Based

**Status:** Accepted  
**Date:** 2026-11-05 (MVP region configuration clarified)

**Context:** Putting everything in one Django app creates a monolithic `models.py` and tangled imports. The spec recommends domain-based separation.

**Decision:** Use the following Django apps:

| App | Owns |
|---|---|
| `accounts` | User model, profiles, authentication |
| `geography` | Future country/region entities and geographic configuration; deferred for MVP |
| `farms` | Farm, FarmZone, FarmBoundaryRevision, FarmSeason |
| `agronomy` | Crop, CropVariety, CropSeasonRule, CropSuitabilityRule, CropRotationRule, and MVP `RegionAgronomyProfile` configuration |
| `earth_data` | DatasetSource, DataFetchJob, EnvironmentalObservation, provider adapters |
| `indicators` | Environmental snapshots, four gauges, derived features |
| `recommendations` | Recommendation, RecommendationOption, RotationStep |
| `simulations` | SimulationRun, SimulationStep |
| `engagement` | CheckIn, ScoreEvent, Badge, UserBadge |
| `verification` | VerificationCase, VerificationItem, ExpertReview, VerificationEvidence |
| `leaderboard` | LeaderboardSnapshot, regional rankings |

For MVP: create only the apps needed by the first vertical slice, then add `accounts`, `farms`, `earth_data`, `agronomy`, `indicators`, `recommendations`, `simulations`, and `engagement` as their phases begin. Do not scaffold unused apps in Phase 1.

Defer: `verification`, `leaderboard`, and a standalone `geography` app. MVP regional crop calendars are keyed by stable `RegionAgronomyProfile.region_code` values owned by `agronomy`; farm APIs use that same `region_code` and optionally `country_code`. This is configuration data, not a general region model.

**Consequences:**
- Each app owns its models and API resources
- Cross-app logic lives in `domain_services/`
- Team members can work on different apps with fewer merge conflicts

---

## ADR-009: JWT Authentication

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The React frontend communicates via REST API. Session-based auth requires CSRF handling for cross-origin requests. JWT tokens are simpler for SPA + API architecture.

**Decision:** Use `djangorestframework-simplejwt` for token-based authentication. Access token + refresh token pattern.

**Consequences:**
- Stateless authentication — no server-side session storage needed
- Frontend stores tokens in memory (not localStorage for security in production)
- CORS configuration is simpler
- Token refresh endpoint handles expiration

---

## ADR-010: GeoJSON as Geometry Interchange Format

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** Farm boundaries need to travel between React (map drawing), DRF API, and PostGIS. GeoJSON is the standard web format for geographic data.

**Decision:** Use GeoJSON for all boundary API requests and responses. Coordinates are `[longitude, latitude]` (GeoJSON convention). Store as SRID 4326 in PostGIS.

**Consequences:**
- Standard format supported by Leaflet, MapLibre, and all GIS tools
- GeoDjango serialization handles GeoJSON natively
- Must validate: valid geometry, closed polygon, reasonable area, within coordinate range

---

## ADR-011: Demonstration Region — Pending Team Decision

**Status:** Proposed (requires team confirmation)  
**Date:** 2026-11-04

**Context:** The spec requires one demonstration region with a local crop/season knowledge set. The team has not confirmed a region.

**Candidate:** Egypt / Nile Delta / Gharbia Governorate

**Rationale for candidate:**
- Two-season agriculture (winter/summer) demonstrates rotation value
- NASA POWER has good coverage
- Well-documented crop systems (wheat, rice, clover/berseem, cotton, maize)
- Team may have local agricultural knowledge
- Arabic/English localization aligns with potential demo

**Decision:** **PENDING TEAM CONFIRMATION.** Do not hardcode this region. Design the system to be region-configurable.

**What confirming a region unlocks:**
- Specific crop catalog with sourced properties
- Specific planting/harvest calendar
- Specific soil and water context
- Meaningful demo data and farmer persona

---

## ADR-012: No Machine Learning Without Justified Dataset

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The spec explicitly warns against ML without suitable training data. The team does not currently have labeled crop outcome data, validated yield data, or disease occurrence records for the demo region.

**Decision:** Use deterministic, explainable rules for the MVP recommendation engine. No ML model training. AI (LLM) is used only for grounded explanation of backend-computed results, as a P1 feature.

**Consequences:**
- Recommendations are fully traceable: input → rule → score → explanation
- No risk of hallucinated predictions
- Can be audited and explained to judges
- ML can be added in P2 when appropriate data exists

---

## ADR-013: Source-Aware Data Classification

**Status:** Accepted  
**Date:** 2026-11-05 (classification taxonomy corrected)

**Context:** The spec requires strict separation between observed data, modeled estimates, user-provided values, and scenario outputs. Mixing them causes scientific misrepresentation.

**Decision:** Every value carries a source-aware `data_category`; broad labels must not conflate retrievals, assimilation/reanalysis, model outputs, or ground measurements:

| Category | Meaning |
|---|---|
| `REMOTE_SENSING_RETRIEVAL` | Product-specific satellite retrieval (for example, a documented satellite soil-moisture or land-surface-temperature retrieval) |
| `REANALYSIS_OR_ASSIMILATION_ESTIMATE` | Meteorological assimilation/reanalysis inputs such as POWER meteorology sourced from MERRA-2/GEOS-IT |
| `MODELLED_ESTIMATE` | Model-derived spatial products such as SoilGrids predictions or SMAP L4 model-assimilation output |
| `GROUND_MEASURED` | Weather-station or laboratory measurement |
| `USER_PROVIDED` | Farmer-entered value (soil test, crop history, etc.) |
| `DERIVED` | Calculated from other values (seasonal sum, anomaly, gauge score) |
| `SCENARIO` | Hypothetical future simulation result |

**Consequences:**
- Frontend can display appropriate labels and disclaimers
- Users understand what is measured vs. modeled vs. hypothetical
- Scientific integrity maintained throughout the pipeline

---

## ADR-014: Host-Local Django Against Compose PostgreSQL/Redis

**Status:** Superseded in part by ADR-018 (2026-11-07) — Django now runs in Compose because
GeoDjango needs native GEOS/GDAL/PROJ. The credential handling and service-reuse decisions
below still apply.  
**Date:** 2026-11-05

**Context:** Phase 1A already provides PostGIS and Redis via Docker Compose with localhost-only published ports. Re-creating those services or putting Django into Compose prematurely would risk replacing working infrastructure.

**Decision:** Run Django on the host against `POSTGRES_HOST=127.0.0.1` and `POSTGRES_PORT` (default 55432). Keep Compose service hostname `postgres` documented for a future in-network Django container. Load shared credentials from the repository-root `.env`. Use `django.db.backends.postgresql` in Phase 1B; defer GeoDjango/`django.contrib.gis` until Phase 2 farm geometry work.

**Consequences:**
- Phase 1A Compose file stays unchanged
- Windows developers reuse the verified Docker database
- Switching to an in-Compose Django service later only requires changing `POSTGRES_HOST` to `postgres`
- PostGIS capabilities remain available in the database image without enabling GeoDjango yet

---

## ADR-015: Django 6.0 and Minimal Phase 1B Dependencies

**Status:** Accepted  
**Date:** 2026-11-05

**Context:** The host development machine uses Python 3.14. Django 6.0 officially supports Python 3.12–3.14 and matches Master Handoff GeoDjango documentation links. Phase 1B must avoid unused packages (Celery, JWT, geospatial Python libs, domain apps).

**Decision:** Pin Django `>=6.0,<6.1` with DRF, `django-cors-headers`, `psycopg[binary]`, and `python-dotenv`. Create only `apps.core` for the health endpoint. Defer Celery (Phase 1D), React (Phase 1C), JWT/auth, and domain apps.

**Consequences:**
- Compatible with the installed Python 3.14 toolchain
- Small dependency surface for hackathon onboarding
- Clear extension path for later phases without scaffolding empty apps

---

## ADR-016: Celery Reuses the Phase 1A Redis Service

**Status:** Accepted  
**Date:** 2026-11-05

**Context:** ADR-004 selects Celery + Redis for background work, and Phase 1A already runs a healthy, localhost-only Redis 7 container. Phase 1D must add a minimal worker without duplicating infrastructure or leaking credentials.

**Decision:** Wire a `config.celery` app to the existing Redis service using environment variables. The broker uses Redis DB 0 and the result backend DB 1; both are derived in `config/settings/base.py` from `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`, with optional `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` overrides. Tasks are discovered from each installed app's `tasks.py`. Only a `core.ping` probe task is added; NASA ingestion and domain tasks are deferred.

**Consequences:**
- No new container or Compose change; the Phase 1A stack is reused unchanged
- Credentials stay in `.env`; no secret is hardcoded in settings or committed
- `celery -A config worker` runs on the host; switching to an in-Compose worker later only needs a different broker URL
- Windows developers must run the worker with `--pool=solo`
- Django imports `config.celery` at startup, so `celery[redis]` becomes a hard backend dependency

---

## ADR-017: Leaflet + Leaflet-Geoman Free for Farm Boundary Mapping

**Status:** Accepted  
**Date:** 2026-11-07  
**Supersedes:** the open "Map library" item in the Phase 0 decision log

**Context:** Phase 2 requires farmers to define a farm boundary by drawing and editing a polygon on a map, exporting it as GeoJSON, and viewing it again. The library must work with React 19 / TypeScript 7 / Vite 8, require no paid tile token or account, and remain usable while offline-ish for a hackathon demo. The audit found no map library installed and listed this as an open team decision.

**Decision:** Use **Leaflet 1.9.x** with **`@geoman-io/leaflet-geoman-free` 2.x** for drawing, editing and removal, wrapped with **`react-leaflet` 5.x**. Verified peer dependencies (2026-11-07): `react-leaflet@5.0.0` requires `react ^19`, `react-dom ^19`, `leaflet ^1.9.0`; `@geoman-io/leaflet-geoman-free@2.20.6` requires `leaflet ^1.2.0`. The project is on React 19.3, so React Leaflet is compatible.

**Required capabilities:**

| Capability | Mechanism |
|---|---|
| Draw farm polygon | `map.pm.enableDraw("Polygon")` |
| Edit polygon vertices | `layer.pm.enable()` |
| Remove polygon | `layer.pm.remove()` / toolbar control |
| GeoJSON export | `layer.toGeoJSON()` → sent as `geometry` |
| GeoJSON display | `L.geoJSON(...)` on an existing farm |
| Future MultiPolygon | Reuse the same GeoJSON layer and send `type: "MultiPolygon"`; the backend stores `MultiPolygonField` |

**Tile source:** OpenStreetMap raster tiles are the prototype candidate, with the URL kept configurable (Vite env var) and visible OSM attribution rendered on the map. The project must follow the OSM tile usage policy: no bulk tile downloads, no offline scraping, and a stateable `User-Agent`/referrer if traffic grows. Switching to another provider only requires changing the tile URL template and attribution text.

**Consequences:**
- No API keys or accounts are needed for the P0 demo
- Leaflet works on both the host dev server and static builds
- Geoman Free covers draw/edit/remove without a paid license
- The frontend must run GeoJSON in EPSG:4326 (`[longitude, latitude]`), matching ADR-010; Leaflet defaults to WGS84 lat/lon and needs coordinate-order care when serializing
- Map components need jsdom plus canvas/`ResizeObserver` stubs under Vitest, or they must be isolated from DOM-heavy tests
- A future 3D/vector-tile or satellite-imagery overlay would require MapLibre; the GeoJSON contract is unchanged if that swap happens
- Dependencies are **not installed yet**; they belong to the Phase 2 frontend mapping task

---

## ADR-018: Dockerized Django Backend for GeoDjango

**Status:** Accepted  
**Date:** 2026-11-07  
**Supersedes:** the run-location part of ADR-014 (host-local Django); ADR-014's credential handling and service reuse still apply

**Context:** Phase 2 needs GeoDjango, which requires the native GEOS, GDAL and PROJ libraries. The audit verified that the Windows development host has none of them, that `pip install GDAL` only offers a source build there, and that simply adding `django.contrib.gis` fails at import time. Installing OSGeo4W per developer is fragile and hard to reproduce across the team (Risk R9 in the risk register).

**Decision:** Run Django inside the existing Compose project. `backend/Dockerfile` uses `python:3.14-slim` (Debian 13 trixie) and installs `libgeos-dev`, `libgdal-dev`, `gdal-bin`, `libproj-dev`, `binutils` and `libpq5`. A `backend` service is added to `infra/compose.yaml` that:

- builds from `backend/` with `backend/.dockerignore`
- loads the repository-root `.env` via `env_file: ../.env`
- overrides `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`, `REDIS_HOST=redis` for the Compose network
- bind-mounts `../backend:/app` for autoreload, with an anonymous volume masking the Windows `.venv`
- publishes `127.0.0.1:8000` and health-checks `GET /api/v1/health/`
- depends on healthy `postgres` and `redis`

Django's database engine becomes `django.contrib.gis.db.backends.postgis` and `django.contrib.gis` is added to `INSTALLED_APPS`. Framework versions are unchanged (Django 6.0.x, DRF 3.18.x, Python 3.14). The React/Vite frontend stays on the host.

**Verified in the running container (2026-11-07):** Python 3.14.10, GDAL 3.10.3, GEOS 3.13.1 (CAPI 1.19.2), PROJ 9.6.0 (data at `/usr/share/proj`), PostgreSQL 17.5 + PostGIS 3.5.2, `GEOSGeometry` round-trip and `ST_Area(...::geography)` working, 13/13 Phase 1 tests passing.

**Consequences:**
- GeoDjango works identically on every developer machine without host GIS installs
- The Phase 1A PostgreSQL/Redis services and volumes are reused unchanged; no data reset
- `docker compose ... up -d` now also starts Django; infrastructure-only workflows still use `up -d postgres redis`
- Docker Desktop with Linux containers becomes a hard prerequisite for backend work
- The host venv is no longer the runtime for the backend; it remains usable for editor tooling only
- Celery workers must also run with the geospatial libraries, i.e. inside the same image (`docker compose exec backend celery ...`) rather than the Windows host
- Bind-mount file watching uses Django's `StatReloader`; large directories must stay masked (`.venv`)
- A production image should later drop `-dev` packages and use a multi-stage build

---

## ADR-019: Built-in Django User + FarmerProfile (no custom user model)

**Status:** Accepted  
**Date:** 2026-11-07  
**Relates to:** ADR-008 (`accounts` owns user/profile), ADR-009 (JWT)

**Context:** Phase 2 needs farmer registration, a display name and profile editing. The project already runs on `django.contrib.auth.User` with auth/admin/sessions migrations applied, and ADR-015 deliberately kept the dependency surface small. Introducing a bespoke `AUTH_USER_MODEL` after migrations exist requires resetting the development database and rewriting the admin/auth foreign keys, for no MVP capability gain. A second authentication system (separate user table) is explicitly out of scope.

**Decision:** Keep `django.contrib.auth.User` as the **single** identity model, and add `accounts.FarmerProfile` as a one-to-one extension holding `display_name` and `preferred_language`. Registration creates the user and its profile in one transaction; JWT (`djangorestframework-simplejwt` 5.5.1, verified against Django 6.0.10) is the only authentication mechanism. Authorization is owner-based: every farm query is filtered by `owner=request.user`, with `IsFarmOwner` as defence in depth.

**Consequences:**
- No destructive database reset, and Phase 1 auth tables stay intact
- Profile fields are added without touching Django's user schema
- `accounts` still owns profile/authentication concerns per ADR-008
- A future custom user model remains possible but would require a planned migration and data move; it is not needed for P0
- Fields that belong to a farm (soil, water, crops, priorities) live in `farms.FarmerContext`, not on the profile, so they cannot be mistaken for global user attributes

---

## ADR-020: Identity-Scoped Client Cache and Session State

**Status:** Accepted  
**Date:** 2026-11-07 (raised by the Phase 2 integration audit)

**Context:** The SPA caches server data with TanStack Query under resource-only keys
(`['farms']`, `['farm', id]`). The audit reproduced an account switch on one browser:
Farmer B's empty farm list stayed cached, so Farmer A's farms did not appear after signing
back in. The reverse order would briefly render one farmer's cached farms to another user.
The onboarding draft in `sessionStorage` had the same cross-identity exposure.

**Decision:** Treat every authentication transition as an identity boundary:

- `queryClient.clear()` runs on successful login, successful registration and sign-out, so no
  server data cached for one identity can be served to another.
- Sign-out also clears the onboarding draft and step cursor (`clearDraft`, `clearStep`).
- Access tokens stay in memory; the refresh token stays in `sessionStorage` (per tab) and is
  exchanged on load so a reload or a token expiry does not sign the farmer out.

**Consequences:**
- No cross-account data exposure through the client cache on shared devices
- One extra refetch per query after each sign-in (negligible for Phase 2 volumes)
- Query keys remain simple resource keys; identity does not need to be embedded in every key
- A saved farm is unaffected: this is purely client-side cache and draft state
- Covered by `src/auth/AuthProvider.test.tsx`

---

## Phase 0 Decision Log and Open Decisions

**Decision date:** 2026-11-05. This log records documentation-level decisions; proposed choices remain provisional where noted.

- **Region/calendar API:** Use `RegionAgronomyProfile.region_code` in the MVP, owned by `agronomy`; no standalone geography app/model is required. Region choice and crop/calendar contents remain team decisions.
- **Data priority:** NASA POWER is the first planned working source. GPM IMERG is an optional Phase 3/P1 stretch integration after POWER, not a prerequisite for the MVP vertical slice.
- **Report export:** P1; the MVP may use an ordinary browser print action only if convenient, without a dedicated export contract.
- **80% gate:** Not in P0. Keep the master handoff's game/product-rule concept deferred to P1 pending a team decision on whether it is needed for judging. If introduced, it must measure plan/input completeness only, never scientific confidence or certification; define required fields and reviewer action before implementation.
- **Authentication identity:** Phase 0 API contract selects `username` as the registration/login identifier and `email` as contact data. Change only before Phase 2 and update the contract consistently if the team decides otherwise.
- **Demo region, farmer persona, crop system, local calendar, crop catalog sources/reviewer, LLM provider, and deployment target:** unresolved team decisions; see `PROJECT_STATUS.md` and `DEVELOPMENT_PLAN.md`.
- **Map library:** resolved 2026-11-07 — Leaflet + Leaflet-Geoman Free with React Leaflet (ADR-017).
- **Backend run location:** resolved 2026-11-07 — Django runs in Docker for GeoDjango (ADR-018), replacing host-local Django from ADR-014.
- **User model:** resolved 2026-11-07 — the built-in `auth.User` is the single identity model, extended by `accounts.FarmerProfile` (ADR-019); no custom user model or second auth system.
- **Data completeness/confidence:** Contract returns explicit assessment states and method metadata; numeric values are illustrative only until denominator, weighting, and evidence-quality methods are approved.


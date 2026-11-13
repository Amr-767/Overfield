# Overfield — Development Plan

**Last updated:** 2026-11-13
**Team size:** 2 persons
**Stack:** Django + DRF + GeoDjango (Dockerized) + PostgreSQL/PostGIS + React (Vite) + Leaflet/Leaflet-Geoman + Celery/Redis  
**Challenge:** NASA Space Apps 2026 — Field Shift: Adapting Farms with NASA Data

---

## MVP Definition

The minimum viable product is a **complete end-to-end farmer journey**:

1. Register → create farm → draw/select boundary → see area
2. Enter current crops, soil info, water, priorities, constraints
3. Request environmental scan → see labeled NASA-sourced indicators
4. Compare 3 rotation strategies (baseline + 2 alternatives)
5. See why each was suggested, evidence, trade-offs, risks, data gaps
6. Explore a labeled scenario simulation (4 time nodes)
7. Commit a strategy and record a seasonal check-in
8. Optionally view points, badges, and a demo leaderboard after the core journey works

Dedicated PDF/CSV report export and the optional 80% plan-completeness review gate are P1, not required for the P0 journey. The 80% value, if adopted later, is a product/input-completeness rule only and never scientific confidence or NASA certification.

---

## Phase Breakdown

### Phase 0 — Project Analysis and Implementation Planning ✅
**Model:** Opus | **Code changes:** None

- Read and analyze complete specifications
- Audit repository state
- Design architecture and create planning documents
- Identify MVP vs. advanced vs. future features
- Identify risks and unknowns
- Maintain substantive risks in [`RISK_REGISTER.md`](RISK_REGISTER.md)

**Acceptance criteria:**
- Planning documents created
- Architecture decisions documented
- Risk register exists with probability, impact, mitigation, owner, fallback, and resolution phase
- Development order defined
- Team role recommendations provided
- Repository audit matches the actual checkout
- P0 API, provenance, region/calendar, geometry, and scope decisions agree across documents

---

### Phase 1 — Project Foundation and Local Development Environment
**Model:** Flash (Opus if architecture issues) | **Code changes:** Foundation only

Phase 1 is executed as incremental slices so infrastructure and application scaffolding stay reviewable:

| Slice | Scope | Status |
|---|---|---|
| **1A** | Docker Compose PostGIS + Redis, `.env.example`, infra README | ✅ Complete |
| **1B** | Django/DRF foundation, env settings, CORS, `/api/v1/health/`, backend tests | ✅ Complete |
| **1C** | React/Vite foundation + frontend health connectivity check | ✅ Complete |
| **1D** | Celery/Redis minimal worker config + test task | ✅ Complete |
| **1E** | Full foundation integration verification (1A–1D end to end) | ✅ Complete |

**Tasks:**
1. Initialize Git with `.gitignore`, `develop` branch
2. Django project: `config/` with split settings (base/dev/prod) — **1B done**
3. Create only the project/configuration structure needed for the first vertical slice; defer unused domain apps until their phase — **1B done**
4. React frontend: Vite + React + basic project structure — **1C done**
5. PostgreSQL + PostGIS configuration — **1A done; Django connected in 1B**
6. `.env.example` with all placeholder variables — **1A/1B done**
7. CORS/CSRF configuration for local dev — **1B done**
8. Health check endpoint: `GET /api/v1/health/` — **1B done**
9. Minimal React-to-Django connectivity check — **1C done**
10. Celery/Redis minimal config + test task — **1D done**
11. API versioning convention: `/api/v1/` — **1B done**
12. Formatting/linting setup — frontend lint (oxlint) and Vitest tests added in 1C; Python formatters (Black, isort, Ruff) and Prettier remain deferred
13. `README.md` with reproducible setup instructions — **1A/1B/1C done**

**Acceptance criteria:**
- Backend starts with documented commands — **met in 1B**
- Frontend starts with documented commands — **met in 1C**
- Local setup is reproducible on supported team machines, including Windows; prefer Docker Compose for PostGIS and Redis with Django/Vite local, or document exact alternatives and versions — **infra + backend met**
- Health endpoint responds successfully — **met in 1B**
- Frontend can call health endpoint — **met in 1C (verified live and via unit tests)**
- Database connection works — **met in 1B**
- Migrations run — **met in 1B**
- Automated starter tests pass — **backend 13 (1B/1D) and frontend 7 (1C) passing**
- README has reproducible instructions — **met for 1A/1B/1C**
- Full foundation integration verified end to end (services, DB, Redis, health, CORS, build, Celery) — **met in 1E**

**Dependencies:** Phase 0 approval

---

### Phase 2 — Accounts, Farms, Geospatial Boundaries, and Farmer Inputs ✅
**Model:** Opus for spatial design, Flash for CRUD | **Code changes:** Backend models + APIs + basic frontend

**Status:** ✅ Complete and integration-audited (2026-11-07). See the Phase 2 Integration Audit in
`PROJECT_STATUS.md`. Dependencies for Phase 3 are satisfied once this branch is merged.

| Slice | Scope | Status |
|---|---|---|
| **Step 0** | Dockerized Django with GDAL/GEOS/PROJ, GeoDjango + PostGIS backend enabled, SimpleJWT compatibility verified, mapping decision recorded (ADR-017/018) | ✅ Complete (2026-11-07) |
| **2A** | `accounts`: `FarmerProfile` on built-in `auth.User` + JWT register/token/refresh/me | ✅ Complete (2026-11-07) |
| **2B** | `domain_services.geometry`: GeoJSON validation, SRID 4326, geodesic area via PostGIS geography | ✅ Complete (2026-11-07) |
| **2C** | `farms` models/APIs (Farm, FarmZone, FarmerContext, FarmCropHistory) with ownership permissions and spatial indexes | ✅ Complete (2026-11-07) |
| **2D** | Frontend auth shell (router, token store, TanStack Query) + register/login screens | ✅ Complete (2026-11-07) |
| **2E** | Frontend 5-step onboarding with Leaflet + Leaflet-Geoman draw/edit/remove, area preview, review, farm list/detail | ✅ Complete (2026-11-07) |

**Environment:** Django runs in the `backend` Compose service (ADR-018). GeoDjango is
enabled with the PostGIS backend; the host has no GDAL/GEOS, so host-local Django is no
longer supported. The map library decision is closed: Leaflet 1.9 + Leaflet-Geoman Free
2.x via React Leaflet 5 (peer-verified against React 19; ADR-017). OSM raster tiles are
the prototype tile source with configurable URL and visible attribution.

**Tasks:**
1. User authentication (JWT via `djangorestframework-simplejwt` — compatibility with Django 6.0 verified in Step 0)
2. `Farm` and `FarmZone` models with GeoDjango `MultiPolygonField` geometry (SRID 4326); cast to geography for geodesic area/distance, and use geometry for overlay/spatial operations
3. GeoJSON validation through DRF serializers
4. Geodesic area calculation from geometry via geography cast (or a justified equal-area projection)
5. Spatial indexes and ownership permissions
6. Farmer context models: soil info, water availability, current rotation, priorities, constraints
7. Frontend: farm creation flow with map (polygon draw or point fallback)
8. Frontend: show boundary and area before submission

**Acceptance criteria:**
- Valid polygon accepted, invalid rejected
- Area calculation returns plausible result for test geometry
- Ownership permissions prevent cross-user access
- Farm creation and retrieval work through real API
- Frontend submits and displays a farm

**Dependencies:** Phase 1 complete; Phase 2 Step 0 complete (geospatial environment)

---

### Phase 3 — NASA Data Providers and Asynchronous Ingestion
**Model:** Opus | **Code changes:** Provider adapters, Celery tasks, data models

**Status:** ✅ COMPLETE, reviewed and merged into `develop` (`37db0b3`, 2026-11-09) — slices 3A–3E plus closeout (provenance, review, throttle assessment).

| Slice | Scope | Status |
|---|---|---|
| **3A** | Read-only NASA POWER audit: verified codes, units, aggregation meaning, fill value, time standard, per-parameter sources, availability | ✅ Complete (2026-11-09) |
| **3B** | Reusable POWER client: stdlib `http.client` transport with separate connect/read timeouts, retries honouring `Retry-After`, query validation, typed errors, parsing/normalisation, TTL cache, 30 mocked tests | ✅ Complete (2026-11-09) |
| **3C** | `earth_data` models + catalogue seed + persistence services: `DatasetSource`, `DataFetchJob`, `EnvironmentalObservation`, idempotent upsert, additive migrations | ✅ Complete (2026-11-09) |
| **3D** | Celery ingestion task: `earth_data.ingest_farm_environment` with bounded retries, one-job-per-farm lock, refresh planning, enqueue helper | ✅ Complete (2026-11-09) |
| **3E** | Environmental data REST API: `POST /farms/{id}/scans/`, `GET /data-jobs/{id}/`, `GET /farms/{id}/environment/daily/` with validation, pagination and owner scoping | ✅ Complete (2026-11-09) |
| **Closeout** | Live-retrieval provenance record, full implementation review, throttle assessment, decimal-contract documentation | ✅ Complete (2026-11-09) |

**Environment additions already prepared:** `NASA_POWER_BASE_URL`,
`NASA_POWER_CONNECT_TIMEOUT_SECONDS`, `NASA_POWER_READ_TIMEOUT_SECONDS`, `NASA_POWER_MAX_RETRIES`,
`NASA_POWER_BACKOFF_SECONDS`, `NASA_POWER_MAX_RETRY_AFTER_SECONDS`, `NASA_POWER_CACHE_TTL_SECONDS`
in `.env.example` (NASA POWER needs no API key).

**Tasks:**
1. Research and verify NASA POWER API (current endpoint, parameters, units, format)
2. Implement NASA POWER adapter with provider interface
3. Evaluate GPM IMERG as a possible second precipitation source; **deferred** — not implemented in Phase 3 or 4 (see `HACKATHON_DATA_SOURCE_MATRIX.md`)
4. `DatasetSource` and `DataFetchJob` models
5. `EnvironmentalObservation` normalized storage model
6. Celery tasks: fetch → normalize → store, with states (PENDING/RUNNING/SUCCEEDED/PARTIAL/FAILED)
7. Timeout, bounded retry, backoff, error logging
8. Idempotent ingestion (no duplicate observations)
9. Scan-status API: `POST /farms/{id}/scans/`, `GET /data-jobs/{id}/`
10. Unit-test provider parsing with representative fixtures
11. Test timeout and failure behavior
12. Keep one documented manual integration test for live NASA access

**Acceptance criteria:**
- One real NASA POWER request for test coordinates succeeds
- Raw response → normalized data pipeline works
- Units, timestamps, source metadata preserved
- Mocked tests pass independently of live NASA
- Duplicate ingestion prevented
- Scan status API works

**Dependencies:** Phase 2 complete

---

### Phase 4 — Environmental Indicators and Data Fusion
**Model:** Opus for design, Flash for implementation | **Code changes:** Indicator services and summary API (no snapshot table, no migrations)

**Status:** ✅ COMPLETE (2026-11-12) — 4A–4E delivered on `phase/4-environmental-engine`. ✅ 4F documentation alignment complete (2026-11-13). Uncommitted; awaiting review/merge.

| Slice | Scope | Status |
|---|---|---|
| **4A** | Indicator methodology audit + approved decisions R13–R20 (region `EG-GH`, no scores, water/heat/soil/market rules, no backfill, no snapshots) | ✅ Complete (2026-11-09) |
| **4B** | `indicators` app foundation: shared contract, coverage/confidence/freshness helpers, water + heat services over stored observations, 55 tests | ✅ Complete (2026-11-09) |
| **4C** | Soil (per-property, provenance, age labels, no composite score) and market (`UNAVAILABLE`, contextual sources only) services + 30 tests | ✅ Complete (2026-11-09) |
| **4D** | `GET /api/v1/farms/{id}/environment/current/` summary endpoint (owner-scoped 404), all four indicators, coverage/freshness/limitations, 6-query budget | ✅ Complete (2026-11-09) |
| **4E** | `ENVIRONMENTAL_INDICATORS.md`, methodology ids, provenance §11, contract examples, 111 indicator tests | ✅ Complete (2026-11-12) |
| **4F** | NASA Space Apps 2026 data-source alignment: `HACKATHON_DATA_SOURCE_MATRIX.md`, integration-status corrections, scientific distinctions, nullable-period contract | ✅ Complete (2026-11-13) |

**Prerequisites:** a valid Phase 3 scan for the farm (observations exist); the demonstration region
decision (Risk R13) is still open and affects only interpretation/copy, not the maths.

**Tasks:**
1. Normalized internal representation for environmental variables
2. Farm-level temporal aggregation (seasonal summaries)
3. Derived indicators: temperature summaries, precipitation totals, dry-spell indicators
4. Data quality/freshness status: available, stale, partial, missing, low_quality
5. Source-aware distinction among remote-sensing retrieval, reanalysis/assimilation estimate, modelled estimate, ground-measured, user-provided, derived, and scenario outputs
6. Missing-data handling (never replace with zero or invent)
7. Summary response contract (computed on demand — **no `FarmEnvironmentalSnapshot` table**; decision R16)
8. Summary API: `GET /farms/{id}/environment/current/`
9. Unit conversion and validation

**Acceptance criteria:**
- Every displayed value has unit, source/product/parameter, period, parameter-specific spatial support, temporal convention, and quality/freshness label
- Missing data is visibly missing, not fabricated
- Aggregation tests pass with known fixtures
- API response contract tests pass

**Dependencies:** Phase 3 complete

---

### Phase 5 — Crop Knowledge Base and Recommendation Engine
**Model:** Opus | **Code changes:** Crop models, catalog, rules, recommendation service

**Tasks:**
1. `Crop`, `CropSeasonRule`, `CropSuitabilityRule`, `CropWaterProfile`, `CropRotationRule` models
2. The team sources the regional crop catalog; minimum crop set, seasons, and traits are determined after selecting the farmer persona and crop system. Acceptable sources are regional extension/agriculture authorities, FAO references where applicable, or peer-reviewed literature. Do not use an LLM as a source for calendars or coefficients. Label unreviewed demo entries as needing expert validation.
3. Recommendation pipeline: validate → hard constraints → soft preferences → generate sequences → evaluate → rank → explain
4. Three strategy types: BASELINE, WATER_EFFICIENT, SOIL_REGENERATION
5. Deterministic, explainable scoring with configurable weights
6. Explanation contract: why_suggested, benefits, tradeoffs, evidence, data_gaps, risks, confidence
7. API: `POST /farms/{id}/recommendations/`, `GET /recommendations/{id}/`

**Acceptance criteria:**
- Baseline matches farmer's actual input
- Alternatives are valid for selected region/calendar
- Every recommendation has explanation and evidence trail
- Hard constraints filter invalid sequences
- Changing priorities changes ranking transparently

**Dependencies:** Phase 4 complete

---

### Phase 6 — Scenario Simulation and Strategy Comparison
**Model:** Opus for design, Flash for implementation | **Code changes:** Scenario models, simulation service, APIs

**Tasks:**
1. `SimulationRun` and `SimulationStep` models
2. Scenario modes: BASELINE, DRY_SCENARIO, HOT_SCENARIO, WATER_EFFICIENT, SOIL_REGENERATION
3. Display checkpoints: Present, +6 months, +1 year, +2 years, mapped to actual selected-region seasons; preserve actual season/calendar dates on every step (the checkpoint is not assumed to be a growing season)
4. Explicit simulation inputs and assumptions
5. User-adjustable temperature/rainfall scenarios within documented bounds
6. Deterministic reproducibility (same inputs → same outputs)
7. API: `POST /simulations/`, `GET /simulations/{id}/`, `GET /simulations/{id}/steps/`

**Acceptance criteria:**
- Changing scenario input produces explainably different results
- UI/API never labels hypothetical adjustment as NASA forecast
- Simulation output is reproducible for same inputs and engine version

**Dependencies:** Phase 5 complete

---

### Phase 7 — Farmer-Facing React Experience and Dashboard
**Model:** Flash for most UI, Opus for complex state | **Code changes:** React screens, components, API integration

**Tasks:**
1. Welcome / initialize mission screen
2. Farm creation/selection flow
3. Map polygon drawing and area display
4. Farmer input forms: crops, soil, water, priorities, constraints
5. Environmental scan flow with loading/success/failure states
6. Environmental summary with source, unit, period, freshness
7. Three strategy cards with explanations
8. Timeline controls displaying simulation results
9. Four elemental gauges as labeled composite indicators
10. Responsive layout and accessibility

**Acceptance criteria:**
- Complete farm-to-recommendation-to-simulation journey works from UI
- No manual database editing required
- Loading, empty, partial, stale, and failed states handled
- Mobile responsive

**Dependencies:** Phase 6 complete

---

### Phase 8 — Strategy Commitment, Check-ins, Gamification, and Rewards
**Model:** Flash for CRUD, Opus for verification logic | **Code changes:** Engagement models, APIs, frontend

P0 scope in this phase is strategy commitment and a self-reported seasonal check-in. Points history, badges, leaderboard, and reward panel are P1 optional engagement features; do not delay the core journey for them.

**Tasks:**
1. `CommittedStrategy` with versioned copy of plan and assumptions
2. `ActionPlan` and `ActionPlanItem` models
3. Seasonal check-in records with status: SELF_REPORTED, PENDING_REVIEW, etc.
4. `ScoreEvent` auditable points ledger
5. `Badge` and `UserBadge` models
6. Regional leaderboard with privacy-conscious display
7. Demo reward panel (static, clearly labeled)

**Acceptance criteria:**
- Check-in labeled as self-reported, not satellite-confirmed
- If the optional points feature is implemented, score history is auditable
- Missing satellite data cannot automatically reduce score
- Ownership/security tests pass

**Dependencies:** Phase 7 complete

The optional 80% review gate is deferred to P1. If brought into scope, first define required inputs, denominator/weights, missing-field lock behavior, `NEEDS_EXPERT_REVIEW` state, and the reviewer action that unlocks the plan. It scores plan completeness only, not evidence quality, scientific confidence, or NASA certification.

---

### Phase 9 — Full Integration, Security, Testing, and Demo Readiness
**Model:** Opus for review, Flash for fixes | **Code changes:** Fixes only

**Tasks:**
1. End-to-end journey audit
2. API contract consistency check
3. Database migration/index review
4. NASA data accuracy and provenance verification
5. Security review: auth, CORS, CSRF, input validation, secrets
6. Error/loading/empty/partial state review in React
7. Mobile responsiveness and accessibility check
8. README, demo instructions, challenge coverage audit

**Acceptance criteria:**
- Complete journey works without manual database edits
- Challenge coverage audit completed
- Demo runbook created
- All known issues documented

**Dependencies:** Phase 8 complete

---

## Feature Classification

### P0 — MVP (must work for demo)

| Feature | Phase |
|---|---|
| User registration and authentication | 2 |
| Farm creation with map polygon + area | 2 |
| Farmer context: current crops, soil, water, priorities | 2 |
| NASA POWER integration (climate/agro context) | 3 |
| Environmental indicators with source/freshness labels | 4 |
| Regional crop catalog with sourced properties | 5 |
| 3 rotation strategies: baseline + 2 alternatives | 5 |
| Explainable recommendations with evidence trail | 5 |
| Scenario simulation (4 time nodes) | 6 |
| Four elemental gauges (composite indicators) | 6–7 |
| Complete React farmer journey | 7 |
| Strategy commitment and basic check-in | 8 |
| Plan/input completeness gate | P1 (deferred; only if team confirms need) |

### P1 — Add only after P0 works

| Feature | Notes |
|---|---|
| Additional NASA dataset (GPM IMERG) | **Phase 5 candidate**, not a Phase 3 stretch. V07B is feasible for Gharbia at 0.1°, but implementation needs an approved schema extension for product run/version, valid-pixel coverage, aggregation method and QA reason (see `HACKATHON_DATA_SOURCE_MATRIX.md` §8). |
| Polygon-based zonal statistics | Requires raster processing |
| SMAP/ECOSTRESS context | Needs Earthdata auth; regional/opportunistic only |
| Seasonal scenario sliders | Climate perturbation UI |
| PDF/CSV report export | For agricultural advisor |
| Points/badges, demo leaderboard, and reward panel | Optional engagement layer after core P0 journey |
| Optional 80% plan-completeness gate and expert-review workflow | Requires agreed fields, denominator, lock behavior, `NEEDS_EXPERT_REVIEW`, and reviewer unlock action; not scientific confidence |
| AI explanation assistant (grounded) | RAG + read-only tools |
| Arabic/English localization | If demo region is Egypt |

**Priority note:** POWER is the only integrated source and remains the P0 dependency. GPM IMERG, SMAP, Landsat/Sentinel-2/HLS, MODIS/VIIRS, ECOSTRESS, GAEZ, SRTM, GLDAS and ERA5 are **evaluated but not integrated**; U.S.-only resources are out of scope for Gharbia. No secondary source may be added without a documented aggregation method and a source-precedence rule.

### Phase 0 Open Decisions (owners)

| Decision | Owner | Status |
|---|---|---|
| Demo region and stable `region_code` | Team | ✅ Resolved 2026-11-09: Gharbia, Egypt — `EG-GH` (ADR-021) |
| Farmer persona, farm scale, crop system, and calendar season set | Team | Open |
| Crop catalog minimum entries and source review | Team, with local agronomy reviewer sought | Open; do not invent crop facts |
| Authentication identity | Amr + team | ✅ Resolved: username login on Django user + `FarmerProfile` (ADR-019) |
| Map library | Haneen | ✅ Resolved 2026-11-07: Leaflet + Leaflet-Geoman Free (ADR-017) |
| Docker Compose vs exact local versions/setup | Amr + Haneen | ✅ Resolved 2026-11-07: Django runs in Compose for GeoDjango (ADR-018) |
| NASA POWER parameter/source mapping and selected variables | Amr + team | ✅ Resolved 2026-11-09: 7 AG parameters verified against the live API |
| Second precipitation source (GPM IMERG) | Team | Open; blocked on an approved observation-schema extension |
| Egyptian farm-gate market prices | Team | Open; MARKET stays `UNAVAILABLE` (R18) |
| LLM provider, if P1 assistant is retained | Backend lead | Deferred |
| Deployment target | Team | Open |
| Dedicated report export and 80% plan gate | Team | P1 deferred; decide only if demo need justifies |

### P2 — Future work (not hackathon)

| Feature | Notes |
|---|---|
| Calibrated crop growth models (DSSAT) | Requires training data |
| Yield/disease/pest prediction ML | Requires labeled datasets |
| Long-term soil-carbon projection | Requires validated model |
| Full raster infrastructure | Requires object storage pipeline |
| Multi-country/global coverage | Requires per-region crop catalogs |
| Autonomous multi-agent workflows | Requires extensive safety review |
| Commercial partner integrations | Requires real partners |
| Automated satellite-based verification | Scientifically unreliable for small farms |

---

## Project Team

| Team Member | Ownership | Responsibilities |
|---|---|---|
| **Amr** | Backend and full-stack architecture | Backend, full-stack architecture, NASA integration and deployment |
| **Haneen** | Frontend and product experience | Frontend, React, UI/UX and frontend integration |

### Shared responsibilities
- Review API contracts and data provenance together.
- Verify scientific claims and challenge alignment before the demo.

---

## Estimated Timeline (Hackathon)

| Phase | Estimated Duration | Parallel Work |
|---|---|---|
| Phase 1 | 2–3 hours | Backend + Frontend can work simultaneously |
| Phase 2 | 4–6 hours | Backend models/API + Frontend map/forms in parallel |
| Phase 3 | 4–6 hours | Backend focus; Frontend can work on Phase 2 UI polish |
| Phase 4 | 3–4 hours | Backend focus; team begins crop catalog research |
| Phase 5 | 6–8 hours | Backend + C collaborate on engine and crop rules |
| Phase 6 | 4–5 hours | Backend + C collaborate on scenarios |
| Phase 7 | 6–8 hours | Frontend focus; Backend supports API fixes |
| Phase 8 | 3–4 hours | Backend + Frontend in parallel |
| Phase 9 | 3–4 hours | All team members |

**Total estimated:** ~35–48 hours of focused development across 3 people.


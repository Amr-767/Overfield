# AgroSpace Quest — Architecture Decision Records

**Last updated:** 2026-11-04

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
**Date:** 2026-11-04

**Context:** The application requires storing farm boundaries as polygons, calculating geodesic areas, performing spatial queries (which grid cells intersect a farm), and supporting spatial indexes. SQLite cannot do this.

**Decision:** Use PostgreSQL with PostGIS extension. Use GeoDjango (`MultiPolygonField` with `geography=True`, SRID 4326) for farm boundaries.

**Consequences:**
- Accurate geodesic area calculations
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
**Date:** 2026-11-04

**Context:** Putting everything in one Django app creates a monolithic `models.py` and tangled imports. The spec recommends domain-based separation.

**Decision:** Use the following Django apps:

| App | Owns |
|---|---|
| `accounts` | User model, profiles, authentication |
| `geography` | Countries, regions, geographic configuration |
| `farms` | Farm, FarmZone, FarmBoundaryRevision, FarmSeason |
| `agronomy` | Crop, CropVariety, CropSeasonRule, CropSuitabilityRule, CropRotationRule, RegionAgronomyProfile |
| `earth_data` | DatasetSource, DataFetchJob, EnvironmentalObservation, provider adapters |
| `indicators` | Environmental snapshots, four gauges, derived features |
| `recommendations` | Recommendation, RecommendationOption, RotationStep |
| `simulations` | SimulationRun, SimulationStep |
| `engagement` | CheckIn, ScoreEvent, Badge, UserBadge |
| `verification` | VerificationCase, VerificationItem, ExpertReview, VerificationEvidence |
| `leaderboard` | LeaderboardSnapshot, regional rankings |

For MVP: prioritize `accounts`, `farms`, `earth_data`, `agronomy`, `indicators`, `recommendations`, `simulations`, `engagement`.

Defer: `verification`, `leaderboard`, `geography` (use simple country_code initially).

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

## ADR-013: Separation of Observed Data, Estimates, and Scenarios

**Status:** Accepted  
**Date:** 2026-11-04

**Context:** The spec requires strict separation between observed data, modeled estimates, user-provided values, and scenario outputs. Mixing them causes scientific misrepresentation.

**Decision:** Every data value in the system carries a `data_category` field:

| Category | Meaning |
|---|---|
| `OBSERVED` | Direct satellite/sensor measurement or retrieval |
| `MODELED_ESTIMATE` | Derived from models (e.g., SoilGrids, SMAP L4 assimilation) |
| `USER_PROVIDED` | Farmer-entered value (soil test, crop history, etc.) |
| `DERIVED` | Calculated from other values (seasonal sum, anomaly, gauge score) |
| `SCENARIO` | Hypothetical future simulation result |

**Consequences:**
- Frontend can display appropriate labels and disclaimers
- Users understand what is measured vs. modeled vs. hypothetical
- Scientific integrity maintained throughout the pipeline


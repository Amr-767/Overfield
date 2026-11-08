# AgroSpace Quest — API Contracts

**Last updated:** 2026-11-07
**Status:** Phase 2 backend implemented — health, authentication/profile, farms, zones, boundary validation and farmer context are live. Environmental scans, recommendations, simulations and gamification remain design-only.  
**Base URL:** `/api/v1/`  
**Authentication:** JWT Bearer via `djangorestframework-simplejwt` 5.5.1 (implemented). All endpoints require a token except health, registration and token obtain/refresh.  
**Format:** JSON  
**Geometry:** GeoJSON with `[longitude, latitude]` ordering; stored as `MultiPolygonField`/`PointField` SRID 4326
**Identity contract:** `username` is the registration/login identifier; `email` is a contact field and is not accepted as the token-login identifier. Identity is Django's built-in `auth.User`, extended by `accounts.FarmerProfile` (ADR-019).

**Scope labels:** Routes marked P0 form the MVP contract; P1/P2 routes are optional/future. Examples are schema fixtures only and contain no verified farm, NASA, agronomic, or performance result unless explicitly identified as farmer-provided.

### Implementation status

| Endpoint | Status |
|---|---|
| `GET /health/` | ✅ Implemented (Phase 1B) |
| `POST /auth/register/` | ✅ Implemented (Phase 2A) |
| `POST /auth/token/` | ✅ Implemented (Phase 2A) |
| `POST /auth/token/refresh/` | ✅ Implemented (Phase 2A) |
| `GET/PATCH/PUT /me/` | ✅ Implemented (Phase 2A) |
| `POST /farms/` | ✅ Implemented (Phase 2C) — boundary or point fallback |
| `GET /farms/`, `GET/PATCH/PUT/DELETE /farms/{id}/` | ✅ Implemented (Phase 2C) |
| `POST /farms/validate-boundary/` | ✅ Implemented (Phase 2C) |
| `GET/POST /farms/{id}/zones/` | ✅ Implemented (Phase 2C) |
| `GET/PUT/PATCH /farms/{id}/context/` | ✅ Implemented (Phase 2D) |
| Sections 4–9 (scans, crops, recommendations, simulations, gamification) | ⏳ Design-only |

**Error responses:** validation failures use DRF's field-keyed shape `{"field": ["message", ...]}`;
authentication failures use `{"detail": "..."}` with `401`, and cross-user access returns
`404` because querysets are owner-filtered.

---

## 1. Authentication

### POST `/api/v1/auth/register/` — P0 — ✅ implemented
Create a new user account and its `FarmerProfile`. Public (no token).

**Request:**
```json
{
  "username": "farmer1",
  "email": "farmer1@example.com",
  "password": "secure_password",
  "display_name": "Ahmed",
  "preferred_language": "en"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "farmer1",
  "email": "farmer1@example.com",
  "display_name": "Ahmed",
  "preferred_language": "en"
}
```

Validation: `username` and `email` must be unique (case-insensitive); the password is checked with
Django's configured password validators (`400` with a `password` field error when too weak).

### POST `/api/v1/auth/token/` — P0 — ✅ implemented
Obtain JWT access + refresh tokens (username + password).

**Request:**
```json
{
  "username": "farmer1",
  "password": "secure_password"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

### POST `/api/v1/auth/token/refresh/` — P0 — ✅ implemented
Refresh access token with a valid refresh token.

**Request:**
```json
{
  "refresh": "eyJ..."
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ..."
}
```

### GET `/api/v1/me/` — P0 — ✅ implemented
Get the authenticated farmer's profile. `PATCH`/`PUT` accept `display_name`, `preferred_language`
and `email` (an email already used by another account is rejected with `400`).

**Response:** `200 OK`
```json
{
  "username": "farmer1",
  "display_name": "Ahmed",
  "email": "farmer1@example.com",
  "preferred_language": "en",
  "created_at": "2026-11-07T14:47:56.166001Z",
  "updated_at": "2026-11-07T14:47:56.166012Z"
}
```

---

## 2. Farms and Zones

### POST `/api/v1/farms/` — P0 — ✅ implemented
Create a farm from a GeoJSON boundary, or from a location point with a farmer-reported area.

**Request (drawn boundary — preferred):**
```json
{
  "name": "North Field",
  "country_code": "EG",
  "region_code": "eg-gharbia",
  "timezone": "Africa/Cairo",
  "boundary": {
    "type": "Polygon",
    "coordinates": [[[30.9501, 30.7901], [30.9522, 30.7901], [30.9522, 30.7918], [30.9501, 30.7918], [30.9501, 30.7901]]]
  },
  "location": { "type": "Point", "coordinates": [30.9511, 30.7909] }
}
```

`boundary` accepts a GeoJSON `Polygon`, `MultiPolygon` or `Feature`; `location` is optional
and, when omitted, defaults to the boundary centroid. The response is normalised to
`MultiPolygon`.

**Request (point-only fallback — lower spatial precision):**
```json
{
  "name": "Point Farm",
  "location": { "type": "Point", "coordinates": [30.95, 30.79] },
  "farmer_reported_area_hectares": "2.5000"
}
```
`farmer_reported_area_hectares` is required when no boundary is supplied; it is stored with
`area_source = FARMER_REPORTED` and `spatial_precision = LOW`.

> **Note:** Coordinates are `[longitude, latitude]`. The example coordinates are for schema
> illustration only, not a real recommended farm.

**Response:** `201 Created`
```json
{
  "id": 42,
  "name": "North Field",
  "country_code": "EG",
  "region_code": "eg-gharbia",
  "boundary": { "type": "MultiPolygon", "coordinates": [[[[30.9501, 30.7901], ...]]] },
  "location": { "type": "Point", "coordinates": [30.95115, 30.79095] },
  "area_hectares": "3.7882",
  "area_source": "GEOMETRY_DERIVED",
  "geometry_source": "BOUNDARY",
  "spatial_precision": "HIGH",
  "timezone": "Africa/Cairo",
  "zone_count": 0,
  "created_at": "2026-11-07T14:48:00Z",
  "updated_at": "2026-11-07T14:48:00Z"
}
```

**Field semantics**

| Field | Meaning |
|---|---|
| `area_hectares` | Always computed server-side. Boundary farms: PostGIS `ST_Area(geometry::geography)` (geodesic, metres). Point farms: the farmer's reported value. |
| `area_source` | `GEOMETRY_DERIVED` or `FARMER_REPORTED` |
| `geometry_source` | `BOUNDARY` or `LOCATION_POINT` |
| `spatial_precision` | `HIGH` for a drawn boundary, `LOW` for a point-only farm |

Any client-supplied `area_hectares` is ignored.

**Validation rules (all return `400` with a `boundary` field error)**

- Geometry type must be `Polygon`/`MultiPolygon` (or a `Feature` wrapping one)
- Coordinates must be `[longitude, latitude]` with lon ∈ [-180, 180] and lat ∈ [-90, 90]
- Rings must be closed and have at least 4 positions
- Geometry must be valid (no self-intersections), non-empty, and have non-zero area
- Computed area must not exceed **10,000 ha** (also catches swapped coordinates)

**Validation errors:** `400 Bad Request`
```json
{
  "boundary": ["Invalid polygon: geometry is not closed (first and last position must match)."],
  "farmer_reported_area_hectares": ["Required when only a location point is supplied (point-only farms cannot have a computed area)."]
}
```

**Verified behaviours (Phase 2 integration audit, 2026-11-07):**

| Input | Result |
|---|---|
| Known 0.0021° × 0.0017° ring | `area_hectares = 3.7882` (geodesic) |
| Same request plus `area_hectares: 999999` | client value ignored; `3.7882` stored |
| Unclosed ring | `400` “geometry is not closed” |
| Self-intersecting ring | `400` “self-intersecting or otherwise invalid” |
| Latitude > 90 (e.g. swapped order) | `400` |
| Ring larger than 10,000 ha | `400` “exceeds the maximum allowed” |
| Empty `coordinates: []` | `400` |
| Boundary farm / point farm | `GEOMETRY_DERIVED` + `HIGH` / `FARMER_REPORTED` + `LOW` |

### GET `/api/v1/farms/` — P0 — ✅ implemented
List the authenticated user's farms, paginated (20/page). Owner-filtered.

### GET `/api/v1/farms/{farm_id}/` — P0 — ✅ implemented
Retrieve farm details. Another user's farm returns `404`.

### PATCH/PUT `/api/v1/farms/{farm_id}/` — P0 — ✅ implemented
Update `name`, `country_code`, `region_code`, `timezone`, `boundary` and/or `location`.
Sending a new `boundary` recomputes `area_hectares` geodesically and resets
`area_source` to `GEOMETRY_DERIVED`. A boundary cannot be cleared; a point-only farm may
update `farmer_reported_area_hectares`.

### DELETE `/api/v1/farms/{farm_id}/` — P1 in Phase 0, ✅ implemented
Delete a farm (owner only) and cascade its zones and context. Returns `204`.

### POST `/api/v1/farms/validate-boundary/` — ✅ implemented
Validate a candidate boundary without saving it (used before submit).
Request `{"boundary": {...}}`; `200` returns `{valid, srid: 4326, area_hectares,
area_method: "postgis_geography", geometry}`; invalid input returns `400`.

### GET `/api/v1/farms/{farm_id}/zones/` — P0 — ✅ implemented
Paginated list of the farm's zones: `{id, farm, name, boundary, area_hectares, notes, created_at}`.

### POST `/api/v1/farms/{farm_id}/zones/` — P0 — ✅ implemented
Create a zone wholly within the farm. Request `{ "name": "North", "boundary": {"type":"Polygon", "coordinates":[...]}, "notes": "" }`;
`201` returns the zone shape above. The zone is rejected with `400` when its geometry is invalid,
falls outside the farm boundary, or exceeds the farm area. Zones are optional and farmer-created;
farms are never split automatically.

---

## 3. Farmer Context and Onboarding

### GET `/api/v1/farms/{farm_id}/context/` — P0 — ✅ implemented
Retrieve the farmer's soil info, water availability, crop history, priorities and constraints.
The context row is created lazily on first read; all measurements default to `null` (unknown).

**Response:** `200 OK`
```json
{
  "farm_id": 42,
  "soil_source": "LAB_TEST",
  "texture_class": "clay_loam",
  "ph": "7.80",
  "organic_carbon_percent": null,
  "nitrogen_ppm": "22.50",
  "phosphorus_ppm": null,
  "potassium_ppm": null,
  "sampling_depth_cm": 30,
  "sampling_method": "composite",
  "lab_name": "Delta Soil Lab",
  "sample_date": "2026-03-15",
  "water_source": "FARMER_REPORTED",
  "irrigation_available": true,
  "irrigation_type": "surface_canal",
  "water_reliability": "seasonal_variable",
  "priorities": {
    "water_conservation": 0.4,
    "soil_regeneration": 0.3,
    "market_income": 0.2,
    "forage_value": 0.1
  },
  "constraints": {
    "equipment": ["no_mechanized_harvester"],
    "seed_availability": "unknown",
    "labor_availability": "family_labor_only"
  },
  "current_crops": [
    {
      "id": 1,
      "season": "Winter 2025/26",
      "crop": "Wheat",
      "crop_code": "",
      "source": "FARMER_REPORTED",
      "notes": ""
    }
  ],
  "created_at": "2026-11-07T14:48:00Z",
  "updated_at": "2026-11-07T14:48:02Z"
}
```

**Provenance (`*_source`)** — `FARMER_REPORTED`, `LAB_TEST`, `EXTERNAL_PROVIDER`,
`REMOTE_SENSING`, `UNKNOWN`. Each crop entry carries its own `source`. Values are never
invented: an absent measurement is `null`, and `null` means *unknown*, not zero or "none".

**Enumerations**

- `texture_class`: `sand`, `loamy_sand`, `sandy_loam`, `loam`, `silt_loam`, `silt`, `clay_loam`,
  `sandy_clay_loam`, `silty_clay_loam`, `clay`, `sandy_clay`, `silty_clay`, `unknown`
- `irrigation_type`: `none`, `surface_canal`, `drip`, `sprinkler`, `flood`, `mixed`, `other`, `unknown`
- `water_reliability`: `reliable`, `seasonal_variable`, `unreliable`, `unknown`

### PUT/PATCH `/api/v1/farms/{farm_id}/context/` — P0 — ✅ implemented
`PATCH` updates the supplied fields only; `PUT` replaces the context. `current_crops` is an
ordered season/crop history (sending it replaces the previous list). Every field is optional.

**Validation (`400`)**

- `ph` must be within 0–14; `organic_carbon_percent` within 0–100
- `priorities` keys are limited to `water_conservation`, `soil_regeneration`, `market_income`,
  `forage_value`; weights must be non-negative and sum to 1 (±0.01) when supplied
- `constraints` keys are limited to `equipment` (list), `seed_availability`, `labor_availability`
- enum fields reject unknown values

---

## 4. Environmental Scan and Data

### POST `/api/v1/farms/{farm_id}/scans/` — P0
Queue an environmental data scan.

**Response:** `202 Accepted`
```json
{
  "job_id": "job_8f23a1",
  "status": "PENDING",
  "message": "Your farm scan has been scheduled.",
  "status_url": "/api/v1/data-jobs/job_8f23a1/"
}
```

### GET `/api/v1/data-jobs/{job_id}/` — P0
Check background job status.

**Response:** `200 OK`
```json
{
  "job_id": "job_8f23a1",
  "status": "SUCCEEDED",
  "started_at": "2026-11-04T12:01:00Z",
  "completed_at": "2026-11-04T12:01:45Z",
  "sources_fetched": ["NASA_POWER"],
  "sources_failed": [],
  "sources_partial": []
}
```

**Possible statuses:** `PENDING`, `RUNNING`, `SUCCEEDED`, `PARTIAL`, `FAILED`

### GET `/api/v1/farms/{farm_id}/environment/current/` — P0
Latest farm environmental summary.

**Response:** `200 OK`
```json
{
  "farm_id": 42,
  "as_of": "2026-11-04T12:00:00Z",
  "indicators": [
    {
      "name": "seasonal_mean_temperature",
      "value": 22.4,
      "unit": "°C",
      "period": {"start": "2026-06-01", "end": "2026-09-30"},
      "source": "NASA_POWER",
      "dataset_product": "POWER parameter source/product to be verified",
      "parameter": "T2M",
      "spatial_support": {"description": "parameter/product-specific native support; verify before use", "native_resolution": null},
      "temporal_convention": "UTC (request must explicitly include time-standard=UTC)",
      "source_record_id": null,
      "processing": {"method": "seasonal mean of valid daily values", "version": "pending"},
      "quality_status": "AVAILABLE",
      "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
      "freshness": "2026-11-01"
    },
    {
      "name": "seasonal_precipitation_total",
      "value": null,
      "unit": "mm",
      "source": "NASA_POWER",
      "parameter": "PRECTOTCORR",
      "dataset_product": "POWER parameter source/product to be verified",
      "spatial_support": {"description": "parameter/product-specific native support; verify before use", "native_resolution": null},
      "temporal_convention": "UTC (request must explicitly include time-standard=UTC)",
      "quality_status": "MISSING",
      "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
      "limitation": "Precipitation data not yet fetched for this period"
    }
  ],
  "data_completeness": {"status": "NOT_ASSESSED", "value": null, "reason": "Required checks, denominator, and weighting policy are pending approval."},
  "confidence": {"status": "NOT_ASSESSED", "reason": "Evidence suitability rubric is pending; confidence is claim-specific and separate from completeness."},
  "limitations": ["SMAP soil moisture not integrated in this version"]
}
```

### GET `/api/v1/farms/{farm_id}/environment/history/` — P1
Contract deferred; not part of MVP.

### GET `/api/v1/farms/{farm_id}/data-sources/` — P1
Contract deferred; not part of MVP.

---

## 5. Crop Catalog

### GET `/api/v1/crops/` — P0
Search sourced crop catalog. Query params: `region_code` (required), optional `season`, `water_class`, `crop_family`. Returns paginated `{id, code, name, scientific_name, crop_family, source_status, evidence_ids}` records; only reviewed/explicitly demo-labeled records are eligible for recommendations.

### GET `/api/v1/crops/{crop_id}/profiles/` — P0
Return crop characteristics, applicability, validation status, and structured source references; absent traits are `null`/unknown.

### GET `/api/v1/regions/{region_code}/crop-calendar/` — P0
`region_code` is a stable slug backed by `agronomy.RegionAgronomyProfile`; no standalone `geography` model is required in the MVP. Returns `{region_code, country_code, timezone, calendar_version, seasons:[{season_code, label, start_month_day, end_month_day, crops:[{crop_code, planting_window, harvest_window, evidence_ids}]}]}`. Return `404` for an unknown/unconfigured code. Values must be sourced; no calendar is selected yet.

---

## 6. Recommendations

### POST `/api/v1/farms/{farm_id}/recommendations/` — P0
Generate crop rotation recommendations.

Stable strategy enum: `BASELINE`, `WATER_EFFICIENT`, `SOIL_REGENERATION`. Return exactly one option per enum when evidence supports all; otherwise return a documented `422` with missing evidence/constraints rather than fabricate a sequence. `BASELINE` exactly reproduces farmer-entered history over the same planning horizon. The strategy labels are intents, not fixed crop sequences. Planning horizon and region calendar are explicit. All scores/benefits in the schema example are illustrative fixtures, not verified results.

**Request:** `region_code` is optional but, if provided, must equal the farm's configured code; `planning_seasons` is a positive count; `priority_weights` is optional and named weights must sum to 1. The response records the selected calendar version and actual season dates.

**Response:** `201 Created`
```json
{
  "recommendation_id": "rec_abc123",
  "farm_id": 42,
  "generated_at": "<UTC timestamp>",
  "engine_version": "rotation-v1.0",
  "planning_horizon": {"season_count": 4, "calendar_version": "fixture-only"},
  "data_completeness": {"status": "NOT_ASSESSED", "value": null, "reason": "Method not approved."},
  "options": [
    {
      "strategy_type": "BASELINE",
      "title": "Current rotation",
      "score": null,
      "score_status": "NOT_ASSESSED",
      "confidence": {"status": "NOT_ASSESSED", "reason": "No approved evidence-quality rubric."},
      "seasons": [
        {"season_code": "<calendar-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<exact-farmer-entry>", "source": "USER_PROVIDED"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<exact-farmer-entry>", "source": "USER_PROVIDED"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<exact-farmer-entry>", "source": "USER_PROVIDED"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<exact-farmer-entry>", "source": "USER_PROVIDED"}
      ],
      "why_suggested": "This is your current crop rotation, used as the comparison baseline.",
      "benefits": [],
      "tradeoffs": [],
      "evidence": [{"evidence_id": "ev_fixture", "dataset_product": "farmer-entered history", "parameter": "current_rotation", "date_range": null, "spatial_support": "farm/user record", "source_record_or_snapshot_id": "fixture-only", "processing_method_version": "identity/v1", "quality_status": "USER_PROVIDED", "relevance": "Defines the comparison baseline; not independently verified."}],
      "data_gaps": ["<include only gaps present in this farmer's record>"],
      "risks_for_local_review": [],
      "assumptions": [],
      "illustrative_fixture": true
    },
    {
      "strategy_type": "WATER_EFFICIENT",
      "title": "Hydra Shield (display label)",
      "score": null,
      "score_status": "NOT_ASSESSED",
      "confidence": {"status": "NOT_ASSESSED", "reason": "No approved evidence-quality rubric."},
      "seasons": [
        {"season_code": "<sourced-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"}
      ],
      "why_suggested": "Illustrative intent only; a factual recommendation requires sourced regional crop water traits and a defined comparison method.",
      "benefits": [], "tradeoffs": [], "evidence": [], "data_gaps": [], "risks_for_local_review": [], "assumptions": [], "illustrative_fixture": true
    },
    {
      "strategy_type": "SOIL_REGENERATION",
      "title": "Nitrogen Battery (display label)",
      "score": null,
      "score_status": "NOT_ASSESSED",
      "confidence": {"status": "NOT_ASSESSED", "reason": "No approved evidence-quality rubric."},
      "seasons": [
        {"season_code": "<sourced-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"},
        {"season_code": "<next-season>", "start_date": "<calendar-date>", "end_date": "<calendar-date>", "crop_code": "<supported-candidate>", "source": "CURATED_CROP_CATALOG"}
      ],
      "why_suggested": "Illustrative intent only; support requires verified crop-family, legume/nitrogen, residue, and regional evidence.",
      "benefits": [], "tradeoffs": [], "evidence": [], "data_gaps": [], "risks_for_local_review": [], "assumptions": [], "illustrative_fixture": true
    }
  ]
}
```

Each `evidence` item is structured: `evidence_id`, `dataset_product` (including version when known), `parameter`, `date_range`, `spatial_support`, `source_record_or_snapshot_id`, `processing_method_version`, `quality_status`, and claim-specific `relevance`. Claims reference evidence IDs; free-text source names alone are insufficient. Empty evidence cannot support a factual benefit claim.

### GET `/api/v1/recommendations/{recommendation_id}/` — P0
Retrieve a recommendation with full explanations.

### GET `/api/v1/farms/{farm_id}/recommendations/` — P1
Contract deferred; not part of MVP.

---

## 7. Simulations

### POST `/api/v1/simulations/` — P0
Create a scenario simulation run.

**Request:**
```json
{
  "farm_id": 42,
  "recommendation_id": "rec_abc123",
  "option_type": "WATER_EFFICIENT",
  "scenario_type": "DRY_SCENARIO",
  "horizon_months": 24,
  "time_nodes": [0, 6, 12, 24],
  "calendar_version": "<region-calendar-version>",
  "adjustments": {
    "rainfall_change_percent": -15,
    "temperature_change_c": 1.0
  }
}
```

> **Note:** `adjustments` are user-selected stress tests, NOT forecasts.

**Response:** `201 Created`
```json
{
  "simulation_id": "sim_xyz789",
  "status": "COMPLETED",
  "scenario_type": "DRY_SCENARIO",
  "engine_version": "scenario-v1.0"
}
```

### GET `/api/v1/simulations/{simulation_id}/` — P0
Get simulation summary.

### GET `/api/v1/simulations/{simulation_id}/steps/` — P0
Get time-step details.

**Response:** `200 OK`
```json
{
  "simulation_id": "sim_xyz789",
  "steps": [
    {
      "step_index": 0,
      "label": "Present",
      "season": "Winter 2026/27",
      "season_start_date": "<calendar-date>",
      "season_end_date": "<calendar-date>",
      "calendar_version": "<region-calendar-version>",
      "crop": "Barley",
      "gauges": {
        "water_resilience": {"score": 74, "label": "Moderate-Good", "confidence": "medium"},
        "heat_adaptability": {"score": 68, "label": "Moderate", "confidence": "medium"},
        "soil_regeneration": {"score": 55, "label": "Moderate", "confidence": "low"},
        "market_value": {"score": null, "label": "Unknown", "confidence": "none"}
      },
      "assumptions": ["Rainfall -15% from 2021-2025 seasonal mean"],
      "data_category": "SCENARIO"
    }
  ]
}
```

---

## 8. Strategy Commitment and Check-ins

### POST `/api/v1/recommendations/{recommendation_id}/commit/` — P0
Commit a selected strategy.

**Request:**
```json
{
  "option_type": "WATER_EFFICIENT"
}
```

**Response:** `201 Created`
```json
{
  "committed_strategy_id": "cs_456",
  "action_plan_id": "ap_789",
  "status": "ACTIVE",
  "next_action": {
    "item_id": "ai_001",
    "action": "Prepare field for barley planting",
    "due_window": "2026-11-15 to 2026-12-01"
  }
}
```

### POST `/api/v1/action-items/{item_id}/check-ins/` — P0
Submit a farmer check-in.

**Request:**
```json
{
  "action_completed": true,
  "notes": "Planted barley on Nov 20",
  "evidence_type": "SELF_REPORTED"
}
```

**Response:** `201 Created`
```json
{
  "checkin_id": "ci_101",
  "status": "SELF_REPORTED",
  "points_awarded": 10,
  "note": "Self-reported action. Not satellite-verified."
}
```

---

## 9. Gamification — P1 (contracts deferred; not part of MVP)

Points, badges, and leaderboards are P1; their contracts are deferred and not part of MVP.

## 10. Report Export and Plan Review Gate

### Report export — P1

Dedicated PDF/CSV export is deferred; no P0 export route is defined. A browser print view may be used as a convenience after the core journey works, without expanding P0 scope.

### 80% review gate — P1, deferred

The master handoff's locked/provisional concept is not part of P0. If adopted later, it must be named a plan/input completeness score, never scientific confidence or NASA certification. Contract and acceptance criteria are deferred until required fields, denominator/weights, fields that lock a plan, and the reviewer action that unlocks it are agreed. The API must not imply this gate currently exists.

---

## 10. Health Check

### GET `/api/v1/health/` — P0 — **implemented (Phase 1B)**
System health check (no authentication required).

**Response:** `200 OK` when the database connection succeeds
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-11-05T18:26:38.885012Z"
}
```

**Response:** `503 Service Unavailable` when the database connection fails
```json
{
  "status": "unhealthy",
  "database": "unavailable",
  "timestamp": "2026-11-05T18:26:38.885012Z"
}
```

---

## Error Format

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error message.",
  "code": "error_code",
  "field_errors": {
    "field_name": ["Specific validation error."]
  }
}
```

**Common status codes:**
- `400` — Validation error
- `401` — Authentication required
- `403` — Permission denied (not the owner)
- `404` — Resource not found
- `429` — Rate limited
- `500` — Server error

---

## Notes

- **Trailing slashes are required** on every path. Django's `APPEND_SLASH` cannot redirect
  `PATCH`/`PUT`/`DELETE` while keeping the body, so `/farms/9` returns `500` while `/farms/9/` works.
  The SPA always uses trailing slashes.
- **Non-owner access returns `404`**, not `403`: farm querysets are filtered by owner, so another
  farmer cannot tell whether a farm id exists. This applies to farm detail, context and zones.
- All endpoints require JWT authentication unless otherwise noted (health check is public).
- All list endpoints are paginated (default: 20 items per page).
- All geometry is GeoJSON with `[longitude, latitude]` coordinate order.
- Area is always calculated server-side; client-provided area values are ignored.
- `null` in farmer context means "unknown" — not "zero" or "no constraint."
- `data_completeness` and claim-specific `confidence` are separate; both remain `NOT_ASSESSED` until defensible calculation methods are approved.
- Scan endpoints return `202 Accepted` and a job ID; the frontend polls the job status.
- Simulation adjustments are labeled as user-selected stress tests, never as NASA predictions or forecasts.


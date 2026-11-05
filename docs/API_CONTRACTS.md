# AgroSpace Quest — API Contracts

**Last updated:** 2026-11-05
**Status:** Phase 0 — Design only. No endpoints implemented yet.  
**Base URL:** `/api/v1/`  
**Authentication:** JWT (Bearer token) via `djangorestframework-simplejwt`  
**Format:** JSON  
**Geometry:** GeoJSON ([longitude, latitude] convention)
**Identity contract:** `username` is the registration/login identifier; `email` is a contact field and is not accepted as the token-login identifier. This is the Phase 0 API choice; the team may revise it before Phase 2 only by updating the contract consistently.

**Scope labels:** Routes marked P0 form the planned end-to-end MVP contract; P1/P2 routes are optional/future. Examples are schema fixtures only and contain no verified farm, NASA, agronomic, or performance result unless explicitly identified as farmer-provided. No endpoint is implemented in Phase 0.

---

## 1. Authentication

### POST `/api/v1/auth/register/` — P0
Create a new user account.

**Request:**
```json
{
  "username": "farmer1",
  "email": "farmer1@example.com",
  "password": "secure_password",
  "display_name": "Ahmed"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "farmer1",
  "email": "farmer1@example.com",
  "display_name": "Ahmed"
}
```

### POST `/api/v1/auth/token/` — P0
Obtain JWT access + refresh tokens.

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

### POST `/api/v1/auth/token/refresh/` — P0
Refresh access token.

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

### GET `/api/v1/me/` — P0
Get current user profile.

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "farmer1",
  "display_name": "Ahmed",
  "email": "farmer1@example.com"
}
```

---

## 2. Farms and Zones

### POST `/api/v1/farms/` — P0
Create a farm with GeoJSON boundary.

**Request:**
```json
{
  "name": "North Field",
  "country_code": "EG",
  "region_code": "<team-selected-stable-code>",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[30.9501, 30.7901], [30.9522, 30.7901], [30.9522, 30.7918], [30.9501, 30.7918], [30.9501, 30.7901]]]
  },
  "timezone": "Africa/Cairo"
}
```

> **Note:** Coordinates are `[longitude, latitude]`. The example coordinates are for schema illustration only, not a real recommended farm.

**Response:** `201 Created`
```json
{
  "id": 42,
  "name": "North Field",
  "country_code": "EG",
  "region_code": "<team-selected-stable-code>",
  "boundary": { "type": "MultiPolygon", "coordinates": [[[[30.9501, 30.7901], ...]]] },
  "area_hectares": "4.2500",
  "timezone": "Africa/Cairo",
  "created_at": "2026-11-04T12:00:00Z"
}
```

**Validation errors:** `400 Bad Request`
```json
{
  "geometry": ["Invalid polygon: geometry is not closed."],
  "area_hectares": ["Calculated area exceeds maximum allowed (10000 ha)."]
}
```

### GET `/api/v1/farms/` — P0
List the authenticated user's farms. Returns paginated farm summaries using the same fields as the create response.

### GET `/api/v1/farms/{farm_id}/` — P0
Retrieve farm details (owner only).

### PATCH `/api/v1/farms/{farm_id}/` — P0
Update farm metadata.

### DELETE `/api/v1/farms/{farm_id}/` — P1
Delete farm (owner only).

### GET `/api/v1/farms/{farm_id}/zones/` — P0
List farm zones; initially may return an empty paginated list. Each item is `{id, name, geometry, area_hectares}`.

### POST `/api/v1/farms/{farm_id}/zones/` — P0
Create a zone wholly within the farm. Request `{ "name": "North", "geometry": {"type":"Polygon", "coordinates":[...]}}`; response `201` returns the item shape above. Invalid or out-of-farm geometry returns `400`.

---

## 3. Farmer Context and Onboarding

### GET `/api/v1/farms/{farm_id}/context/` — P0
Retrieve the farmer's current crop routine, soil info, water, priorities, and constraints.

**Response:** `200 OK`
```json
{
  "farm_id": 42,
  "current_crops": [
    {"season": "Winter 2025/26", "crop": "Wheat", "source": "FARMER_REPORTED"}
  ],
  "soil_info": {
    "source": "FARMER_LAB_TEST",
    "texture_class": "clay_loam",
    "ph": 7.8,
    "organic_carbon_percent": null,
    "sampling_depth_cm": 30,
    "method": null,
    "lab_name": null,
    "sample_date": "2026-03-15"
  },
  "water_availability": {
    "irrigation_available": true,
    "irrigation_type": "surface_canal",
    "water_reliability": "seasonal_variable"
  },
  "priorities": {
    "water_conservation": 0.4,
    "soil_regeneration": 0.3,
    "market_income": 0.2,
    "forage_value": 0.1
  },
  "constraints": {
    "equipment": ["no_mechanized_harvester"],
    "seed_availability": "UNKNOWN",
    "labor_availability": "family_labor_only"
  }
}
```

### PUT/PATCH `/api/v1/farms/{farm_id}/context/` — P0
Save/update farmer context using the response fields above. `current_crops` is an ordered season/crop history and baseline source; `soil_info` includes source, sampling depth/method/date and nullable measurements; `water_availability` includes irrigation access/type/reliability; `priorities` are named relative weights (must be non-negative and sum to 1 when supplied); `constraints` are explicit values or unknown. `null` means unknown, not "no constraint." Return `200` with the normalized saved context.

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

### GET `/api/v1/health/` — P0
System health check (no authentication required).

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-11-04T12:00:00Z"
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

- All endpoints require JWT authentication unless otherwise noted (health check is public).
- All list endpoints are paginated (default: 20 items per page).
- All geometry is GeoJSON with `[longitude, latitude]` coordinate order.
- Area is always calculated server-side; client-provided area values are ignored.
- `null` in farmer context means "unknown" — not "zero" or "no constraint."
- `data_completeness` and claim-specific `confidence` are separate; both remain `NOT_ASSESSED` until defensible calculation methods are approved.
- Scan endpoints return `202 Accepted` and a job ID; the frontend polls the job status.
- Simulation adjustments are labeled as user-selected stress tests, never as NASA predictions or forecasts.


# AgroSpace Quest — API Contracts

**Last updated:** 2026-11-04  
**Status:** Phase 0 — Design only. No endpoints implemented yet.  
**Base URL:** `/api/v1/`  
**Authentication:** JWT (Bearer token) via `djangorestframework-simplejwt`  
**Format:** JSON  
**Geometry:** GeoJSON ([longitude, latitude] convention)

---

## 1. Authentication

### POST `/api/v1/auth/register/`
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

### POST `/api/v1/auth/token/`
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

### POST `/api/v1/auth/token/refresh/`
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

### GET `/api/v1/me/`
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

### POST `/api/v1/farms/`
Create a farm with GeoJSON boundary.

**Request:**
```json
{
  "name": "North Field",
  "country_code": "EG",
  "region_name": "Gharbia",
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
  "region_name": "Gharbia",
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

### GET `/api/v1/farms/`
List the authenticated user's farms.

### GET `/api/v1/farms/{farm_id}/`
Retrieve farm details (owner only).

### PATCH `/api/v1/farms/{farm_id}/`
Update farm metadata.

### DELETE `/api/v1/farms/{farm_id}/`
Delete farm (owner only).

### GET/POST `/api/v1/farms/{farm_id}/zones/`
List or create zones within a farm.

---

## 3. Farmer Context and Onboarding

### GET `/api/v1/farms/{farm_id}/context/`
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

### PUT/PATCH `/api/v1/farms/{farm_id}/context/`
Save/update farmer context. `null` means unknown, not "no constraint."

---

## 4. Environmental Scan and Data

### POST `/api/v1/farms/{farm_id}/scans/`
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

### GET `/api/v1/data-jobs/{job_id}/`
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

### GET `/api/v1/farms/{farm_id}/environment/current/`
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
      "product": "T2M daily",
      "spatial_support": "0.5° grid cell",
      "quality_status": "AVAILABLE",
      "data_category": "OBSERVED",
      "freshness": "2026-11-01"
    },
    {
      "name": "seasonal_precipitation_total",
      "value": null,
      "unit": "mm",
      "source": "NASA_POWER",
      "quality_status": "MISSING",
      "data_category": "OBSERVED",
      "limitation": "Precipitation data not yet fetched for this period"
    }
  ],
  "data_completeness": 0.65,
  "limitations": ["SMAP soil moisture not integrated in this version"]
}
```

### GET `/api/v1/farms/{farm_id}/environment/history/`
Historical trend data for the farm.

### GET `/api/v1/farms/{farm_id}/data-sources/`
Show available data sources and their freshness.

---

## 5. Crop Catalog

### GET `/api/v1/crops/`
Search the crop catalog. Supports query params: `region`, `season`, `water_class`, `crop_family`.

### GET `/api/v1/crops/{crop_id}/profiles/`
Return crop characteristics with sources.

### GET `/api/v1/regions/{region_id}/crop-calendar/`
Return regional planting/harvest windows.

---

## 6. Recommendations

### POST `/api/v1/farms/{farm_id}/recommendations/`
Generate crop rotation recommendations.

**Response:** `201 Created`
```json
{
  "recommendation_id": "rec_abc123",
  "farm_id": 42,
  "generated_at": "2026-11-04T12:05:00Z",
  "engine_version": "rotation-v1.0",
  "data_completeness": 0.78,
  "options": [
    {
      "strategy_type": "BASELINE",
      "title": "Traditional Path",
      "score": 62,
      "confidence": "medium",
      "seasons": [
        {"season": "Winter 2026/27", "crop": "Wheat", "source": "farmer_reported"}
      ],
      "why_suggested": "This is your current crop rotation, used as the comparison baseline.",
      "benefits": ["Familiar practice", "Known market"],
      "tradeoffs": ["Continuous cereal may deplete soil nitrogen over time"],
      "evidence": ["NASA POWER climate summary (2021–2026)", "Farmer-reported crop history"],
      "data_gaps": ["No soil test provided for organic carbon"],
      "risks_for_local_review": ["Long-term monoculture pest pressure not assessed"],
      "assumptions": ["Current water access continues unchanged"]
    },
    {
      "strategy_type": "WATER_EFFICIENT",
      "title": "Hydra Shield",
      "score": 78,
      "confidence": "medium",
      "seasons": [
        {"season": "Winter 2026/27", "crop": "Barley"}
      ],
      "why_suggested": "Lower estimated water demand may reduce irrigation pressure.",
      "benefits": ["Estimated 15–25% lower seasonal water demand vs. baseline"],
      "tradeoffs": ["Local barley market price is unknown"],
      "evidence": ["Regional crop water profile (source: FAO Irrigation Manual)"],
      "data_gaps": ["Market price data not available"],
      "risks_for_local_review": ["Barley variety suitability needs local confirmation"],
      "assumptions": ["Crop coefficient from FAO reference, not field-calibrated"]
    }
  ]
}
```

### GET `/api/v1/recommendations/{recommendation_id}/`
Retrieve a recommendation with full explanations.

### GET `/api/v1/farms/{farm_id}/recommendations/`
List recommendation history for a farm.

---

## 7. Simulations

### POST `/api/v1/simulations/`
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

### GET `/api/v1/simulations/{simulation_id}/`
Get simulation summary.

### GET `/api/v1/simulations/{simulation_id}/steps/`
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

### POST `/api/v1/recommendations/{recommendation_id}/commit/`
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

### POST `/api/v1/action-items/{item_id}/check-ins/`
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

## 9. Gamification

### GET `/api/v1/me/points/`
Current points and score history.

### GET `/api/v1/me/badges/`
Earned badges.

### GET `/api/v1/leaderboards/regions/{region_code}/`
Regional ranking (opted-in users only, privacy-conscious).

---

## 10. Health Check

### GET `/api/v1/health/`
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
- Scan endpoints return `202 Accepted` and a job ID; the frontend polls the job status.
- Simulation adjustments are labeled as user-selected stress tests, never as NASA predictions or forecasts.


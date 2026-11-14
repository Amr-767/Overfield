# Overfield — API Contracts

**Last updated:** 2026-11-14
**Status:** Phase 5 — health, auth/profile, farms/zones/context, NASA POWER scans, job status, daily observations, the four-indicator environmental summary, the crop catalogue/profile/calendar APIs and the Phase 5.3 rotation evidence engine are live. Only NASA POWER is integrated; other datasets in the NASA Space Apps 2026 guide are evaluated but not integrated (`HACKATHON_DATA_SOURCE_MATRIX.md`). Simulations and gamification remain design-only.
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
| `POST /farms/{id}/scans/` | ✅ Implemented (Phase 3E) |
| `GET /data-jobs/{id}/` | ✅ Implemented (Phase 3E) |
| `GET /farms/{id}/environment/daily/` | ✅ Implemented (Phase 3E) |
| `GET /farms/{id}/environment/current/` | ✅ Implemented (Phase 4D) |
| `POST /farms/{id}/recommendations/`, `GET /recommendations/{id}/`, `/compare/`, `/explanation/` | ✅ Implemented (Phase 5.3); evidence-gated, owner-scoped, no scores |
| Crop catalogue/profile/calendar APIs | ✅ Implemented (Phase 5.1–5.3); no approved production crop profiles/calendar yet |
| Simulations and gamification | ⏳ Design-only |

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

**Response:** `200 OK` — example from the development demo farm (`window_days=7`); values are real
serializer output, not hand-written.
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

All three endpoints require JWT and are **owner-scoped**: another farmer's farm or job returns
`404`. They are implemented in `apps.earth_data` (Phase 3E).

### POST `/api/v1/farms/{farm_id}/scans/` — P0 — ✅ implemented

Queue a NASA POWER fetch for one farm. The view validates the request, plans the smallest window
still missing data, creates the `DataFetchJob`, and enqueues the Celery task
`earth_data.ingest_farm_environment`; it performs **no** provider HTTP itself.

**Request (all fields optional):**
```json
{
  "start": "2025-06-01",
  "end": "2025-06-30",
  "parameters": ["T2M", "PRECTOTCORR"],
  "force": false
}
```

* `start`/`end` default to `NASA_FETCH_DEFAULT_DAYS` (365) ending `NASA_FETCH_LATENCY_DAYS` (3)
  before today.
* `parameters` default to the seven verified codes.
* `force: true` re-fetches even when every day already has data.

**Response:** `202 Accepted`
```json
{
  "status": "QUEUED",
  "farm_id": 42,
  "job_id": "eaab5b85-4b9d-48fe-bc49-f9035515f4b1",
  "task_id": "3c599ef9-88c3-4c58-a3ab-ff1cb6424705",
  "start": "2025-06-01",
  "end": "2025-06-30",
  "parameters": ["T2M", "PRECTOTCORR"],
  "status_url": "/api/v1/data-jobs/eaab5b85-4b9d-48fe-bc49-f9035515f4b1/"
}
```

| Situation | Status | Body |
|---|---|---|
| Queued | `202` | as above |
| Data already complete for the window | `200` | `{status: "already_current", farm_id, start, end, parameters, detail}` — no job, no provider call |
| Another scan is RUNNING for this farm | `409` | `{status: "already_running", farm_id, job_id, detail, status_url}` |
| Invalid range / parameter / availability | `400` | field-keyed validation errors |
| Broker unavailable | `503` | `{detail, job_id, status: "failed"}`; the job is recorded as `FAILED` |

**Validation rules**

* ISO dates (`YYYY-MM-DD`); `start <= end`
* window ≤ `NASA_FETCH_MAX_RANGE_DAYS` (366)
* `start >= 1981-01-01`, `end <= today`
* parameter `start` must be ≥ that parameter's first available date (solar: `1984-01-01`)
* parameter codes must exist in the active catalogue (unknown → `400` listing supported codes)
* at most 20 parameters

### GET `/api/v1/data-jobs/{job_id}/` — P0 — ✅ implemented

Application-level status of one fetch operation. UUID `job_id`.

**Response:** `200 OK`
```json
{
  "job_id": "eaab5b85-4b9d-48fe-bc49-f9035515f4b1",
  "farm_id": 42,
  "provider": "NASA_POWER",
  "status": "PARTIALLY_SUCCEEDED",
  "requested_start": "2025-06-01",
  "requested_end": "2025-06-30",
  "parameters": ["T2M", "PRECTOTCORR"],
  "days_requested": 30,
  "days_stored": 30,
  "days_missing": 2,
  "error_code": "",
  "error_message": "",
  "created_at": "2026-11-09T13:00:00Z",
  "started_at": "2026-11-09T13:00:01Z",
  "finished_at": "2026-11-09T13:00:03Z",
  "duration_ms": 2100,
  "status_url": "/api/v1/data-jobs/eaab5b85-4b9d-48fe-bc49-f9035515f4b1/"
}
```

**Statuses:** `PENDING`, `RUNNING`, `SUCCEEDED`, `PARTIALLY_SUCCEEDED`, `FAILED`.
`days_missing` counts days with at least one missing parameter; a partially successful scan is
normal when POWER has not published recent days yet.

> **Job status vs Celery state.** The `DataFetchJob` row is the application-level truth. Expected
> provider failures (`PowerRequestError`, `PowerResponseError`, exhausted `PowerTransientError`)
> are recorded on the job and the task returns a `failed` summary — the Celery state is `SUCCESS`
> because the failure was handled. Unexpected internal errors are recorded and then re-raised, so
> Celery reports `FAILURE` with a traceback for operators. Never infer data availability from the
> Celery state; read the job.

### GET `/api/v1/farms/{farm_id}/environment/daily/` — P0 — ✅ implemented

Paginated daily observations for the farm.

**Query parameters:** `start`, `end` (ISO dates, default = last 365 days ending 3 days ago),
`parameter` (one code or comma-separated, repeatable), `page`.

**Response:** `200 OK`
```json
{
  "farm_id": 42,
  "count": 49,
  "next": "http://127.0.0.1:8000/api/v1/farms/42/environment/daily/?page=2",
  "previous": null,
  "range": {"start": "2025-06-01", "end": "2025-06-07"},
  "parameters": [
    {
      "code": "T2M",
      "units": "C",
      "long_name": "Temperature at 2 Meters",
      "product": "MERRA-2",
      "daily_aggregation": "MEAN",
      "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
      "first_available_date": "1981-01-01"
    }
  ],
  "spatial": {
    "requested": {"longitude": "30.998000", "latitude": "30.787000"},
    "returned": {"longitude": "30.998000", "latitude": "30.787000"},
    "time_standard": "UTC",
    "native_resolution_note": "0.5 deg x 0.625 deg (MERRA-2 native grid)",
    "note": "Values are provider grid-cell estimates for the farm's representative point, not on-farm measurements."
  },
  "results": [
    {
      "date": "2025-06-01",
      "parameter": "T2M",
      "long_name": "Temperature at 2 Meters",
      "value": "24.9500",
      "unit": "C",
      "quality_status": "AVAILABLE",
      "source": "NASA_POWER",
      "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
      "time_standard": "UTC",
      "fetch_job_id": "eaab5b85-4b9d-48fe-bc49-f9035515f4b1"
    }
  ]
}
```

`value` is `null` with `quality_status: "MISSING"` when POWER has not published that day; missing
values are never imputed. Raw provider payloads are not returned.

**Decimal serialization (intentional).** Values are emitted as precision-preserving strings
(`"24.9500"`), matching `area_hectares`, because DRF's default `COERCE_DECIMAL_TO_STRING` avoids
binary-float drift. Frontends must convert explicitly for charts/aggregations:
`Number(row.value)` (or `parseFloat`) and keep the `null` check first — `Number(null)` is `0`, which
would silently turn a missing day into a zero reading. If a raw number is preferred later, switch the
field to `FloatField` in `ObservationSerializer` and note the precision change in this contract.

**Rate limiting (pre-public-deployment requirement).** `POST /scans/` has **no DRF throttle** yet.
Current guards are the database-level one-RUNNING-job-per-farm constraint (`409`), the Celery
`rate_limit=12/m` on the ingestion task, and the bounded 366-day window. That is adequate for the
private development environment, but a public deployment needs per-user throttling — recommended
`ScopedRateThrottle` at roughly **10 scans/hour and 60 reads/minute per user** (scans are expensive:
one round-trip to POWER plus up to 2,566 writes). Tracked in `PROJECT_STATUS.md` as a blocker for
public exposure, deliberately not implemented in Phase 3.

**Validation (`400`)**: invalid date format, `start > end`, window > 366 days, future `end`,
date before 1981-01-01, parameter before its first available date, unknown parameter.

### GET `/api/v1/farms/{farm_id}/environment/current/` — P0 — ✅ implemented (Phase 4D)

Unified environmental summary: **WATER, HEAT, SOIL, MARKET** in one response.

**Data-source scope (Phase 4).** Only NASA POWER observations are integrated. This endpoint reads stored
`EnvironmentalObservation` rows from the POWER catalogue; it does not query GPM, SMAP, Landsat,
Sentinel-2, HLS, MODIS/VIIRS, ECOSTRESS, SRTM, GLDAS, ERA5, GAEZ or GEDI. The evaluated-but-not-integrated
datasets and their limitations are documented in
[`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md).

**Authentication:** JWT required. **Ownership:** the farm is resolved with `owner=request.user`;
another farmer's farm or an unknown id returns `404`, anonymous returns `401`. The owner always gets
`200`, even when every indicator is `INSUFFICIENT_DATA`/`UNAVAILABLE`.

**Query parameters**

| Name | Type | Default | Rules |
|---|---|---|---|
| `window_days` | integer | `30` | `1–366`; non-integer or out-of-range → `400` with a `window_days` field error |

The window applies to the **time-series** indicators (water, heat). Soil uses the sample date and
market has no observation period, so neither is given the climate window.

**Definition of "current" (important).** The endpoint does **not** return real-time weather. The
window ends at the **latest available observation** for the farm and spans `window_days` back from
that date. `window.latest_observation`, `window.age_days` and `window.freshness` make stale data
obvious. With no observations, the window ends today and every time-series indicator reports
`INSUFFICIENT_DATA` — no values are invented.

**Response:** `200 OK`
```json
{
  "farm_id": 4,
  "generated_at": "2026-11-12T13:19:23.377559Z",
  "window": {
    "start": "2025-08-01",
    "end": "2025-08-07",
    "days": 7,
    "latest_observation": "2025-08-07",
    "age_days": 462,
    "freshness": "STALE"
  },
  "data_status": "OK",
  "freshness": {
    "latest_observation": "2025-08-07",
    "age_days": 462,
    "status": "STALE"
  },
  "indicators": {
    "water": {
      "code": "WATER",
      "label": "Water",
      "status": "OK",
      "score": null,
      "confidence": "MEDIUM",
      "as_of": "2025-08-07",
      "period": {
        "start": "2025-08-01",
        "end": "2025-08-07",
        "latest_observation": "2025-08-07",
        "age_days": 462,
        "freshness": "STALE"
      },
      "coverage": {
        "days_expected": 7,
        "days_covered": 7,
        "days_missing": 0,
        "ratio": "1.0000",
        "by_parameter": {
          "PRECTOTCORR": 7
        }
      },
      "completeness": null,
      "summary": "all 7 days observed: 0 mm of rainfall over covered days, 0 rainy day(s) at or above 1.0 mm, longest observed dry run 7 day(s).",
      "measurements": [
        {
          "name": "precipitation_total",
          "value": "0.0000",
          "unit": "mm",
          "source": "NASA_POWER",
          "parameter": "PRECTOTCORR",
          "product": "MERRA-2",
          "quality": "AVAILABLE",
          "method": "sum of daily totals over covered days only",
          "interpretation": null
        },
        {
          "name": "rainy_days",
          "value": 0,
          "unit": "days",
          "source": "NASA_POWER",
          "parameter": "PRECTOTCORR",
          "product": "MERRA-2",
          "quality": "AVAILABLE",
          "method": "days with precipitation >= 1.0 mm/day",
          "interpretation": null
        }
      ],
      "context": [
        {
          "name": "irrigation_available",
          "value": "yes",
          "unit": "boolean",
          "source": null,
          "parameter": null,
          "product": null,
          "quality": "FARMER_REPORTED",
          "method": "farmer-entered",
          "interpretation": null
        }
      ],
      "drivers": [
        {
          "name": "Rainfall over covered days",
          "direction": "NEUTRAL",
          "value": "0.0000",
          "unit": "mm"
        }
      ],
      "missing": [
        {
          "name": "soil_moisture",
          "impact": "Plant-available water and water stress cannot be assessed.",
          "required_for": "water stress"
        }
      ],
      "methodology": {
        "id": "water.rainfall.v1",
        "version": "1.0.0",
        "description": "Rainfall summary over the latest available observation window: total, rainy days, maximum daily rainfall and longest observed dry run. No soil-moisture, evapotranspiration or irrigation modelling.",
        "threshold_source": "Rainy-day threshold defaults to 1.0 mm/day (configurable via INDICATOR_RAINY_DAY_MM). No crop or regional threshold is assumed."
      },
      "sources": [
        {
          "provider": "NASA_POWER",
          "parameter": "PRECTOTCORR",
          "units": "mm/day",
          "product": "MERRA-2",
          "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
          "native_resolution_note": "0.5 deg x 0.625 deg (MERRA-2 native grid)",
          "time_standard": "UTC",
          "access_date": "2026-11-09"
        }
      ],
      "limitations": [
        "Values are NASA POWER MERRA-2 grid-cell estimates for the farm's representative point, not on-farm measurements."
      ]
    },
    "heat": {
      "code": "HEAT",
      "label": "Heat",
      "status": "OK",
      "score": null,
      "confidence": "MEDIUM",
      "as_of": "2025-08-07",
      "period": {
        "start": "2025-08-01",
        "end": "2025-08-07",
        "latest_observation": "2025-08-07",
        "age_days": 462,
        "freshness": "STALE"
      },
      "coverage": {
        "days_expected": 7,
        "days_covered": 7,
        "days_missing": 0,
        "ratio": "1.0000",
        "by_parameter": {
          "T2M": 7,
          "T2M_MAX": 7,
          "T2M_MIN": 7
        }
      },
      "completeness": null,
      "summary": "all 7 days observed: mean daily maximum 37.5357 °C and mean daily minimum 22.98 °C; 7 day(s) at or above 35 °C, 0 at or above the very-hot band; 0 cool night(s). Generic exposure only; not crop stress or frost.",
      "measurements": [
        {
          "name": "mean_temperature",
          "value": "29.3186",
          "unit": "C",
          "source": "NASA_POWER",
          "parameter": "T2M",
          "product": "MERRA-2",
          "quality": "AVAILABLE",
          "method": "mean of daily mean temperature over covered days",
          "interpretation": null
        },
        {
          "name": "mean_daily_maximum",
          "value": "37.5357",
          "unit": "C",
          "source": "NASA_POWER",
          "parameter": "T2M_MAX",
          "product": "MERRA-2",
          "quality": "AVAILABLE",
          "method": "mean of daily maximum temperature over covered days",
          "interpretation": null
        }
      ],
      "context": [],
      "drivers": [
        {
          "name": "Hot days",
          "direction": "NEGATIVE",
          "value": 7,
          "unit": "days"
        }
      ],
      "missing": [
        {
          "name": "crop_heat_thresholds",
          "impact": "Crop-specific heat stress cannot be assessed; thresholds are generic air-temperature bands.",
          "required_for": "crop heat risk"
        }
      ],
      "methodology": {
        "id": "heat.exposure.v1",
        "version": "1.0.0",
        "description": "Air-temperature exposure summary over the latest available observation window: mean, mean daily maximum/minimum, and counts of days above/below generic air-temperature thresholds. Not a crop-stress assessment.",
        "threshold_source": "Generic exposure bands, configurable via INDICATOR_HOT_DAY_C (35), INDICATOR_VERY_HOT_DAY_C (40) and INDICATOR_COOL_NIGHT_C (5). Not agricultural or crop-specific thresholds."
      },
      "sources": [
        {
          "provider": "NASA_POWER",
          "parameter": "T2M",
          "units": "C",
          "product": "MERRA-2",
          "data_category": "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
          "native_resolution_note": "0.5 deg x 0.625 deg (MERRA-2 native grid)",
          "time_standard": "UTC",
          "access_date": "2026-11-09"
        }
      ],
      "limitations": [
        "Air-temperature exposure at a MERRA-2 grid cell, not a field or canopy measurement."
      ]
    },
    "soil": {
      "code": "SOIL",
      "label": "Soil",
      "status": "OK",
      "score": null,
      "confidence": "HIGH",
      "as_of": "2026-03-15",
      "period": {
        "start": "2026-03-15",
        "end": "2026-03-15",
        "latest_observation": "2026-03-15",
        "age_days": 242,
        "freshness": "FRESH"
      },
      "coverage": null,
      "completeness": {
        "properties_expected": 6,
        "properties_present": 6,
        "ratio": "1.0000"
      },
      "summary": "6 of 6 soil properties recorded; source LAB_TEST; sample dated 2026-03-15 (FRESH); pH 7.80 (ALKALINE), texture clay_loam. No soil-health score is produced.",
      "measurements": [
        {
          "name": "ph",
          "value": "7.80",
          "unit": "pH",
          "source": "LAB_TEST",
          "parameter": null,
          "product": null,
          "quality": "LAB_TEST",
          "method": "composite",
          "interpretation": "ALKALINE"
        },
        {
          "name": "organic_carbon_percent",
          "value": "1.20",
          "unit": "%",
          "source": "LAB_TEST",
          "parameter": null,
          "product": null,
          "quality": "LAB_TEST",
          "method": "composite",
          "interpretation": null
        }
      ],
      "context": [
        {
          "name": "sample_date",
          "value": "2026-03-15",
          "unit": "date",
          "source": "LAB_TEST",
          "parameter": null,
          "product": null,
          "quality": "LAB_TEST",
          "method": "recorded sample date",
          "interpretation": null
        }
      ],
      "drivers": [
        {
          "name": "Soil properties recorded",
          "direction": "NEUTRAL",
          "value": "6/6",
          "unit": null
        }
      ],
      "missing": [],
      "methodology": {
        "id": "soil.properties.v1",
        "version": "1.0.0",
        "description": "Per-property soil reporting from the farmer context: pH, organic carbon, N/P/K, texture, sampling metadata and sample age. No composite soil-health score.",
        "threshold_source": "pH bands are descriptive (ACIDIC < 6.0, NEUTRAL 6.0-7.5, ALKALINE > 7.5). Sample-age labels are operational (INDICATOR_SOIL_FRESH_MONTHS=12, INDICATOR_SOIL_STALE_MONTHS=24). No crop-suitability or nutrient thresholds."
      },
      "sources": [],
      "limitations": [
        "No composite soil-health score is produced; each property is reported on its own."
      ]
    },
    "market": {
      "code": "MARKET",
      "label": "Market",
      "status": "UNAVAILABLE",
      "score": null,
      "confidence": "NONE",
      "as_of": null,
      "period": null,
      "coverage": null,
      "completeness": null,
      "summary": "No verified local market price source is available for Gharbia (EG), so market value cannot be assessed. No price is estimated or invented.",
      "measurements": [],
      "context": [],
      "drivers": [
        {
          "name": "Local market price source",
          "direction": "NEUTRAL",
          "value": "unavailable",
          "unit": null
        }
      ],
      "missing": [
        {
          "name": "local_market_prices",
          "impact": "No local farm-gate or wholesale price series is available for this region.",
          "required_for": "market value"
        }
      ],
      "methodology": {
        "id": "market.unavailable.v1",
        "version": "1.0.0",
        "description": "Market value is not assessed: no verified local farm-gate price source exists for the demonstration region. National reference series are documented as context only.",
        "threshold_source": "No price thresholds or scoring are defined (decision R18)."
      },
      "sources": [],
      "limitations": [
        "No synthetic, demo or manually curated prices are used (decision R18)."
      ]
    }
  },
  "limitations": [
    "Indicators describe the latest available observations, not real-time or forecast conditions.",
    "Environmental values are NASA POWER grid-cell estimates for the farm's representative point, not on-farm measurements.",
    "The analysis window applies to the time-series indicators (water, heat); soil and market are not time-series indicators.",
    "Market value is unavailable: no verified local farm-price source exists for this region."
  ]
}
```

**Indicator statuses:** `OK`, `PARTIAL`, `INSUFFICIENT_DATA`, `NOT_ASSESSED`, `UNAVAILABLE`.
`score` is always `null` in Phase 4 (decision R14). `confidence` is `NONE`/`LOW`/`MEDIUM`/`HIGH`
(coverage-based, capped at `MEDIUM` for grid-cell sources). `freshness` is reported separately.

**Nullable `as_of` / `period`:** `period` is `null` when an indicator has no observation period — always
for `MARKET`, and for `SOIL` when no sample date is recorded. `as_of` is `null` in the same cases. The
`period` object is never fabricated to fill the climate window.

**Top-level `data_status` semantics** (market is excluded because it is `UNAVAILABLE` by design):

| Condition | `data_status` |
|---|---|
| Water, heat and soil are all `OK` | `OK` |
| At least one of water/heat/soil is `OK` or `PARTIAL` | `PARTIAL` |
| None of water/heat/soil can be assessed | `INSUFFICIENT_DATA` |

**Missing-data behaviour:** missing days are never zero; totals/counts cover observed days only;
`coverage` reports expected/covered/missing; `missing[]` explains what could not be assessed; soil
returns `INSUFFICIENT_DATA` when no context exists and `PARTIAL` when only some properties are known.

**Performance:** one owner-filtered farm lookup, one latest-date aggregate, one window query for all
seven parameters, one catalogue query and one farmer-context query — **6 queries** regardless of the
window size (asserted in tests).

### GET `/api/v1/farms/{farm_id}/environment/history/` — P1
Contract deferred; not part of MVP.

### GET `/api/v1/farms/{farm_id}/data-sources/` — P1
Contract deferred; not part of MVP.

---

## 5. Crop Catalog

### GET `/api/v1/crops/` — P0
Implemented in Phase 5.1/5.2. Authentication is required. `region_code` is required;
an omitted value returns `400` (the catalogue is never implicitly unscoped).
Returns `{count, next, previous, results}` where each result has `id`, `code`, `name`,
`scientific_name`, `crop_family`, `source_status`, and `evidence_ids`. A crop is region-ready
only when it has reviewer-approved traits (`approval_status = APPROVED`,
`validation_status = VALID`) whose **reviewer-decided** applicability is `DIRECT`,
`GENERAL`, or `TRANSFERABLE_LIMITED`; `US_SPECIFIC` evidence and unreviewed source claims are
deliberately excluded. Current production result: empty, because no individual agricultural
dataset is approved for import and no trait has passed review.

### GET `/api/v1/crops/{crop_id}/profiles/` — P0
Implemented in Phase 5.1/5.2. Returns the list fields plus `characteristics` and
`missing_characteristics`. Every characteristic preserves raw/normalized value and
units (null stays null), cultivar/variety, temporal and geographic applicability,
the source's applicability claim, `approval_status`, `approved_geographic_applicability`,
`applicability_justification`, validation status, source record ID/URL and evidence reference.
`source` contains dataset identifier, publisher, version, DOI, licence, attribution and
official landing page URL. Internal source-file paths and import errors are never exposed.

### GET `/api/v1/regions/{region_code}/crop-calendar/` — P0 — implemented
Returns only an approved `RegionAgronomyProfile`, including calendar version, source references, season dates, crop associations and evidence identifiers. An unknown or unapproved calendar returns `404`. No Gharbia calendar is currently approved, so `/EG-GH/crop-calendar/` returns `404` until reviewed evidence is entered.

---

## 6. Recommendations

### POST `/api/v1/farms/{farm_id}/recommendations/` — P0 — Phase 5.3 implemented
Generate a reproducible crop-rotation evidence assessment. Authentication is required and farm ownership is enforced (`404` for another user's farm).

**Request:** `region_code` is optional but must match the configured farm region, `planning_seasons` is 1–12 (default 4), and optional named `priority_weights` must sum to 1. No candidate crop sequence is accepted from the client.

The current engine returns an explicit history-only `BASELINE` when sufficient unambiguous farmer history exists. It may also return evidence-feasible calendar sequences but does not rank them or assign them an intent. `WATER_EFFICIENT` and `SOIL_REGENERATION` strategies are not emitted until reviewed preference methods exist. Candidate alternatives come only from approved calendar/profile evidence. Missing information yields a persisted `201` assessment with `INSUFFICIENT_EVIDENCE`, not fabricated options or a `422`.

**Response:** `201 Created`, including when the correct result is `INSUFFICIENT_EVIDENCE`. The id identifies an immutable input/evidence snapshot; `input_sha256` plus `engine_version` permits audit and reproduction. Scores are always null and options may be empty. The pre-existing example below is illustrative only; it is not a factual output. In the current production state, the catalogue has no approved Gharbia profiles or calendar, so an empty `options` list and explicit `missing` reasons are expected.
```json
{
  "recommendation_id": "<uuid>",
  "status": "INSUFFICIENT_EVIDENCE",
  "missing": [
    {"name": "regional_crop_calendar", "reason": "No approved, source-backed crop calendar is configured for EG-GH."},
    {"name": "eligible_crop_profiles", "reason": "No approved source-backed crop profiles are available for this region."}
  ],
  "options": [],
  "input_sha256": "<sha256>"
}
```

<!-- Historical schema sketch only: not emitted by the implemented API. The contract above is authoritative.
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

-->

Each implemented option includes the exact crop sequence, relevant farmer history, sourced crop traits, evidence identifiers, evaluated/not-evaluated constraints, explicit data gaps, assumptions, and a null score. Environmental rows are stored with dates, parameter, units, product, quality and freshness, but are not used for suitability because no approved crop-period/threshold mapping currently exists.

### GET `/api/v1/recommendations/{recommendation_id}/` — P0 — implemented
Retrieve the stored reproducible assessment, evidence snapshot, missing data and limitations. Cross-user retrieval is `404`.

### GET `/api/v1/recommendations/{recommendation_id}/explanation/` — implemented
Retrieve the explanation and evidence/constraint provenance from the same immutable assessment.

### GET `/api/v1/recommendations/{recommendation_id}/compare/?with={other_id}` — implemented
Compare two owner-scoped assessment records and report whether their input hashes match. This does not produce an objective ranking or numeric score.

### GET `/api/v1/farms/{farm_id}/recommendations/` — P1
Contract deferred; not part of MVP.

---

## 7. Simulations

Implemented in Phase 6 as **environment-only scenario simulation**. The earlier planned shape
(0–100 gauges, crop-level horizons, `POST /api/v1/simulations/` with `farm_id` in the body) is
superseded: no approved regional crop catalogue or calendar exists, and Phase 6 forbids scores.
Crop-level requests are refused with `400`.

All endpoints require authentication and are owner-scoped: anonymous is `401`, another
farmer's farm or run is `404`.

### POST `/api/v1/farms/{farm_id}/simulations/` — implemented

**Request:**
```json
{
  "scenario_mode": "CUSTOM",
  "window_days": 30,
  "temperature_delta_c": "2.00",
  "rainfall_multiplier": "0.70"
}
```

- `scenario_mode`: `BASELINE`, `HOT_SCENARIO`, `DRY_SCENARIO`, `CUSTOM` (default `BASELINE`).
- `HOT_SCENARIO` is fixed at `+2.00 °C`; `DRY_SCENARIO` is fixed at `rainfall × 0.70`.
- `CUSTOM` accepts `temperature_delta_c` in `[-5.00, 5.00]` and `rainfall_multiplier` in
  `[0.20, 2.00]`; at least one is required.
- `window_days` is `1–366` (default 30) and ends at the farm's latest usable observation.
- `planning_seasons`, `crop_codes`, `strategy` and similar keys return `400` because they need
  an approved regional calendar that does not exist.

**Response:** `201 Created` — stored run with `simulation_id`, `scenario`, `status`
(`COMPLETED` or `INSUFFICIENT_EVIDENCE`), `baseline`, `steps`, `differences`, `comparison`
(`score: null`, `ranked: false`), `crop_level_outcomes: "NOT_SIMULATED"`,
`hypothetical_notice`, `limitations` and `input_sha256`.

### GET `/api/v1/farms/{farm_id}/simulations/` — implemented
Recent stored runs for one owned farm (`{count, results}`), newest first.

### GET `/api/v1/simulations/{simulation_id}/` — implemented
Stored run, including all steps.

### GET `/api/v1/simulations/{simulation_id}/steps/` — implemented
Stored checkpoints only (`{simulation_id, engine_version, steps, hypothetical_notice,
crop_level_outcomes}`).

Each step carries `checkpoint`, `label`, `horizon_months`, `as_of_date` (`null` until an
approved calendar anchors a real date), `status`, `metrics`, `missing_inputs`,
`applied_adjustments`, `assumptions` and `limitations`. Values are environment-only;
missing observations stay `null`. No step claims a future observation or a forecast.

### Determinism
`input_sha256` is the SHA-256 of a canonical, sorted-key JSON snapshot of the farm id, engine
version, scenario definition, thresholds and stored values. The same inputs and engine version
produce byte-identical output and the same hash. Adjustments are labelled
`HYPOTHETICAL` / `USER_DECLARED_ASSUMPTION` everywhere.

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

- **Environmental values are strings** (`"24.9500"`); convert with `Number(value)` after checking
  for `null`.
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


# AgroSpace Quest — Data Provenance Registry

**Last updated:** 2026-11-09
**Status:** Phase 3 — live NASA POWER retrievals recorded (development environment).

---

## Purpose

This document records every data source used in AgroSpace Quest: the exact product, variables, units, spatial/temporal support, access method, quality flags, processing steps, known limitations, and retrieval dates.

**Every number displayed to a user must be traceable to an entry in this registry.**

---

## 1. NASA POWER — Agroclimatology (MVP Primary Source)

| Field | Value |
|---|---|
| **Provider** | NASA Langley Research Center |
| **Product** | POWER (Prediction of Worldwide Energy Resources) |
| **Community** | AG (Agroclimatology) |
| **API Endpoint** | `https://power.larc.nasa.gov/api/temporal/daily/point` |
| **Documentation** | [Daily API docs](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) |
| **Spatial Support / Resolution** | Parameter/product-specific and inherited from the original source; record the specific source product and support for every requested parameter. Do not assign one generic POWER grid. POWER meteorological MERRA-2 fields are described at 0.5° latitude × 0.625° longitude; this must not be generalized to all POWER parameters. |
| **Temporal Resolution** | Daily |
| **Temporal Coverage** | 1981-01-01 to near-real-time. **Verified 2026-11-09:** `T2M`/`PRECTOTCORR` valid from 1981-01-01; `ALLSKY_SFC_SW_DWN` valid only from **1984-01-01**. Observed latency ≈2 days (2026-11-08/09 returned the fill value on 2026-11-09). |
| **Format** | JSON, CSV |
| **Authentication** | None required (public API) |
| **Rate Limits** | Not formally documented; avoid excessive concurrent requests |
| **Time Standard** | The Daily API defaults to Local Solar Time (LST). The planned convention is UTC and every request must explicitly include `time-standard=UTC`; persist the requested and returned convention with the record. |

### Source classification and parameter provenance

POWER is an API/distribution service over multiple source products, not a single observation type. Meteorological parameters originate from assimilation/reanalysis products including MERRA-2 and GEOS-IT. Solar parameters are inferred from satellite observations using radiative-transfer methods. Set classification per parameter/product after verifying its documented source; do not label all POWER data as direct observations. The examples below are candidate parameters only and remain subject to catalog/unit verification.

Official references: [POWER meteorological sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/), [POWER data sources FAQ](https://power.larc.nasa.gov/docs/faqs/data/), [POWER methodology](https://power.larc.nasa.gov/docs/methodology/).

### MVP Variables (to verify against current parameter catalog)

| Parameter Code | Meaning | Unit | AgroSpace Use |
|---|---|---|---|
| `T2M` | Temperature at 2 m | °C | Daily temperature context |
| `T2M_MAX` | Maximum 2-m temperature | °C | Heat exposure summaries |
| `T2M_MIN` | Minimum 2-m temperature | °C | Night-time temperature, frost screening |
| `PRECTOTCORR` | Corrected precipitation | mm/day | Historical rainfall totals and dry-spell detection |
| `RH2M` | Relative humidity at 2 m | % | Humidity context |
| `WS2M` | Wind speed at 2 m | m/s | Optional ET/context inputs |
| `ALLSKY_SFC_SW_DWN` | All-sky surface shortwave downward radiation | MJ/m²/day (verified 2026-11-09) | Solar/radiation context |

### Important Limitations

- **NOT a weather forecast.** POWER provides historical and near-real-time data. Future projections require a separate forecast provider.
- **NOT a field weather station.** Values represent gridded model/reanalysis estimates for a grid cell, not an on-farm sensor.
- **Latency exists.** Recent days may not have data available yet.
- Exact parameter availability, units, and communities should be re-verified against the [POWER Parameter Catalog](https://power.larc.nasa.gov/docs/methodology/) before implementation.

### Processing Steps (planned)

1. Request daily data for farm centroid coordinates and specified date range with explicit `time-standard=UTC`
2. Parse JSON response; validate parameter keys and units
3. Handle missing values and fill/sentinel values per POWER documentation
4. Store as `EnvironmentalObservation` records with source metadata
5. Aggregate to seasonal summaries in the indicators layer

### Verified request/response facts (2026-11-09, API `v2.10.3`)

| Fact | Verified value |
|---|---|
| Fill / missing sentinel | `header.fill_value = -999.0`; `null` also treated as missing. Both map to `None`, never stored as a number. |
| Time standard | Daily defaults to **LST**; every request must send `time-standard=UTC` and the client asserts `header.time_standard` echoes `UTC`. Daily means differ between standards (T2M 16.15 °C UTC vs 16.17 °C LST on 2024-01-01). |
| Daily aggregation | `T2M` = mean of 24 hourly values (verified 22.6621 → 22.66); `PRECTOTCORR` = **daily total** (verified hourly sum 0.42 = daily 0.42); `T2M_MAX`/`T2M_MIN` are daily extremes and are rejected by the hourly endpoint. |
| Returned coordinates | `geometry.coordinates = [lon, lat, elevation_m]`, snapped to **0.001°** (request 30.9512/30.7909 → 30.951/30.791/4.96). This is **not** the model grid-cell centre. |
| Native resolution | MERRA-2 **½° lat × ⅝° lon** (0.5° × 0.625°). The “0.5° × 0.5°” figure in the daily docs applies to **regional** requests only. |
| Per-parameter source | `T2M`, `PRECTOTCORR` → `merra2`; `RH2M`, `WS2M` → `merra2,power` (derived); `ALLSKY_SFC_SW_DWN` → `syn1deg` (from the `x-data-sources` response header). |
| CERES SYN1deg resolution | **Not verified** — the methodology page currently 404s. Do not display or claim a solar resolution until confirmed. |
| Limits | ≤20 parameters per point request; `community` is required; start before 1981-01-01 → `422`; unknown parameter → `422` with `messages[]`. No `RateLimit-*` headers are exposed; docs warn that repeated identical requests to one location can be blocked (client caches identical queries). |
| Error shape | `{"header": "...", "messages": ["..."]}` (HTTP 422) and FastAPI-style `{"detail": [...]}` for bad parameters. |

### Retrieval Date

Read-only verification requests executed **2026-11-09** (audit + client smoke check).

### Live retrievals (Phase 3D/3E)

Three real retrievals were executed against the live API through the Celery worker and are stored in
the development database. Every figure below was read back from `earth_data_datafetchjob` /
`earth_data_environmentalobservation`; nothing is estimated.

**Source and request shape (verified on both jobs)**

| Field | Value |
|---|---|
| Provider / product | NASA POWER, Daily Point API `https://power.larc.nasa.gov/api/temporal/daily/point` |
| Community | `AG` (Agroclimatology) |
| Format | `JSON` |
| Time standard | `UTC` (requested and echoed in `header.time_standard`) |
| API version | `v2.10.3` (`POWER Daily API`) |
| Farm | id 4 — "Demo - North Field (Gharbia)", boundary farm |
| Representative point | `POINT_ON_SURFACE` of the largest boundary part |
| Requested coordinates | longitude `30.998000`, latitude `30.787000` |
| Returned coordinates | longitude `30.998000`, latitude `30.787000`, elevation `4.96 m` |

**Run 1 — full MVP parameter set (Phase 3D worker check)**

| Field | Verified value |
|---|---|
| Job id | `eaab5b85-4b9d-48fe-bc49-f9035515f4b1` |
| Parameters | `T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN, WS2M` |
| Requested range | 2025-06-01 → 2025-06-07 (7 days) |
| Observations stored | **49** (7 parameters × 7 days), 0 missing |
| Job status | `SUCCEEDED`, `days_stored = 7`, `days_missing = 0` |
| Retrieval timestamps | created `2026-11-09T13:30:48.173137Z`, finished `2026-11-09T13:30:50.125018Z`, duration `1953 ms` |
| Reported products | `MERRA2`, `SYN1DEG`, `POWER` |

**Run 2 — two parameters (Phase 3E API smoke check)**

| Field | Verified value |
|---|---|
| Job id | `48e3caf4-c545-4fa6-97c7-8c31192f4c88` |
| Parameters | `T2M`, `PRECTOTCORR` |
| Requested range | 2025-07-01 → 2025-07-07 (7 days) |
| Observations stored | **14** (7 × `T2M` + 7 × `PRECTOTCORR`), 0 missing |
| Job status | `SUCCEEDED`, `days_stored = 7`, `days_missing = 0` |
| Retrieval timestamps | created `2026-11-09T13:49:19.078831Z`, finished `2026-11-09T13:49:20.445107Z`, duration `1367 ms` |
| Reported products | `MERRA2` only (no solar parameter requested) |
| Verification | `GET /api/v1/farms/4/environment/daily/?start=2025-07-01&end=2025-07-07&parameter=T2M` returned 7 rows; `GET /api/v1/data-jobs/{id}/` returned `SUCCEEDED` |

**Run 3 — review probe completing the July window (full parameter set)**

| Field | Verified value |
|---|---|
| Job id | `f1f7cd76-dea5-4477-96d4-a9acb39dfe83` |
| Parameters | `T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN, WS2M` |
| Requested range | 2025-07-01 → 2025-07-07 |
| Observations (this job) | **49**; the 14 rows from Run 2 were updated in place, not duplicated |
| Job status | `SUCCEEDED`, `days_stored = 7`, `days_missing = 0` |
| Retrieval timestamps | created `2026-11-09T14:02:28.289178Z`, finished `2026-11-09T14:04:12.717438Z`, duration `104434 ms` (worker started after the task had been queued) |
| Reported products | `MERRA2`, `SYN1DEG`, `POWER` |

After the three runs the database holds **98 observation rows** for farm 4 (49 for June, 49 for July),
which also demonstrates the idempotent upsert: re-running a window updates rows instead of adding them.

**`T2M` daily-mean values stored for Run 2 (°C, read from the database)**

| Date | Value (°C) |
|---|---|
| 2025-07-01 | 31.09 |
| 2025-07-02 | 30.09 |
| 2025-07-03 | 31.22 |
| 2025-07-04 | 29.85 |
| 2025-07-05 | 29.41 |
| 2025-07-06 | 29.18 |
| 2025-07-07 | 29.78 |

`PRECTOTCORR` values for the same days are stored (units `mm/day`) and are queryable through the daily
endpoint; they are omitted here to keep this entry readable.

**Known limitations of these retrievals**

- Values are **grid-cell estimates**, not on-farm measurements. MERRA-2 meteorological parameters use a
  0.5° × 0.625° grid; the farm spans a small fraction of one cell.
- The returned coordinates are POWER's 0.001°-rounded echo of the requested point (identically equal
  here). They do **not** identify the underlying model grid-cell centre, so the exact cell cannot be
  derived from the response.
- `ALLSKY_SFC_SW_DWN` (Run 1) comes from CERES SYN1deg; its native resolution remains unverified and is
  therefore left blank in the catalogue rather than asserted.
- Values are published to two decimals; the platform stores them as `Decimal(10, 4)` without rounding
  the source precision further.
- Near-real-time latency is not visible in these runs because both windows are historical (2025).

**Not recoverable / not recorded**

- The API's internal timing metadata (`times.data`, `times.process`) and the raw JSON response body were
  not persisted; only normalised observations, coordinates, units, API version and response product
  list were stored.
- The exact wall-clock time of the underlying provider computation is unknown; the timestamps above are
  when the platform executed and completed the fetch.

---

## 2. NASA GPM IMERG — Precipitation Estimates (MVP Candidate #2)

| Field | Value |
|---|---|
| **Provider** | NASA Goddard Space Flight Center |
| **Product** | GPM IMERG (Integrated Multi-satellitE Retrievals for GPM) |
| **Version** | V07 (verify current version before implementation) |
| **Documentation** | [IMERG overview](https://gpm.nasa.gov/data/imerg), [Data directory](https://gpm.nasa.gov/data/directory), [V07 tech docs](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation) |
| **Spatial Resolution** | ~0.1° × 0.1° (~10 km) for common gridded products |
| **Temporal Resolution** | Half-hourly (aggregated to daily/monthly) |
| **Processing Runs** | Early (low latency), Late (moderate latency), Final (gauge-adjusted, best for research) |
| **Authentication** | May require NASA Earthdata Login for some access paths |
| **Format** | HDF5, NetCDF, GeoTIFF depending on access method |

### MVP Variables

| Variable | Unit | AgroSpace Use |
|---|---|---|
| Precipitation rate / accumulation | mm/hr or mm | Rainfall totals, dry-spell counts, seasonal anomalies, heavy-rain events |

### Important Limitations

- Satellite precipitation estimates, not rain gauge measurements
- Biases possible in mountainous terrain, coastlines, intense convection
- Early/Late runs are less accurate than Final
- Must convert rates to accumulations correctly (rate × time interval)
- ~10 km pixel may cover many farms; not a field-level measurement

### Access Method (to research)

- Direct download from GES DISC or Giovanni
- AppEEARS for point/area subsets (verify GPM product availability)
- NASA Earthdata Login required for most access paths

### Integration Priority

**P1 / optional Phase 3 stretch goal, after POWER.** Only integrate if the team can confidently retrieve, aggregate, and quality-check the data within the available time. NASA POWER precipitation (`PRECTOTCORR`) can serve as the initial precipitation context; it is itself source-classified from its exact POWER parameter provenance.

### Retrieval Date

Not yet retrieved.

---

## 3. NASA SMAP — Soil Moisture Context (P1 Scope)

| Field | Value |
|---|---|
| **Provider** | NASA / NSIDC DAAC |
| **Product** | SMAP Enhanced L3 Radiometer Global Daily 9 km (SPL3SMP_E) |
| **Version** | Version 6 (verify current version) |
| **Documentation** | [NSIDC SMAP overview](https://nsidc.org/data/smap), [SPL3SMP_E V6](https://nsidc.org/data/spl3smp_e/versions/6) |
| **Spatial Resolution** | 9 km EASE-Grid 2.0 |
| **Temporal Resolution** | Daily (AM/PM overpasses) |
| **Variable** | Surface soil moisture (volumetric water content, m³/m³) |
| **Authentication** | NASA Earthdata Login required |

### Important Limitations

- 9 km pixel can contain many farms and land-cover types
- **NOT field-level root-zone moisture** — it is a surface estimate
- L4 products are model-assimilation, not direct retrieval
- Vegetation, frozen ground, water bodies affect the signal
- Cannot prove individual farmer irrigation from SMAP alone

### Integration Priority

**P1 scope.** Include only after NASA POWER is working and if Earthdata authentication is set up.

### Retrieval Date

Not yet retrieved.

---

## 4. NASA ECOSTRESS — Thermal/ET Context (P1 Scope)

| Field | Value |
|---|---|
| **Provider** | NASA / LP DAAC |
| **Product** | ECOSTRESS LST&E, ET, ESI products |
| **Documentation** | [Product spec table](https://ecostress.jpl.nasa.gov/data/product-specification-documents-table), [Data resources](https://nasa.github.io/ECOSTRESS-Data-Resources/) |
| **Spatial Resolution** | Commonly tens of meters (varies by product — verify specific product) |
| **Temporal Resolution** | Irregular (ISS orbit-dependent), not daily guaranteed |
| **Authentication** | NASA Earthdata Login required |
| **Access Method** | AppEEARS for area/point subsetting |

### Important Limitations

- Land-surface temperature ≠ 2-m air temperature
- Irregular revisit — data gaps are normal
- Cloud cover eliminates observations
- Product-specific quality flags and units must be applied
- Missing overpass ≠ zero stress

### Integration Priority

**P1 scope.** Only integrate when LST/ET adds demonstrable value and valid coverage exists for the demo region.

### Retrieval Date

Not yet retrieved.

---

## 5. Non-NASA Local Data Sources (MVP Required)

### 5.1 Crop Catalog (Regional)

| Field | Value |
|---|---|
| **Type** | Curated regional crop knowledge |
| **Status** | NOT YET CREATED — needs team research |
| **Required Content** | Common name, scientific name, crop family, season windows, water demand class, heat/drought tolerance, N-fixation potential, residue/cover traits, pest/disease rotation rules |
| **Source** | Must be sourced from regional agricultural extension services, FAO references, or peer-reviewed literature. **NOT from LLM generation.** |
| **Validation** | Needs local agronomist review (mark as "demo data — needs expert validation" if unreviewed) |

### 5.2 Soil Information

| Field | Value |
|---|---|
| **Primary source** | Farmer-entered soil test results |
| **Fallback** | SoilGrids 250m modeled estimates (clearly labeled as modeled, not measured) |
| **SoilGrids docs** | [ISRIC SoilGrids](https://isric.org/explore/soilgrids) |
| **Required fields** | Texture class, pH, organic carbon, sampling depth, method, date |
| **Limitation** | SoilGrids values are spatial predictions with prediction intervals — not direct field samples |

### 5.3 Market Prices

| Field | Value |
|---|---|
| **Status** | NOT AVAILABLE for MVP |
| **Approach** | Accept farmer-entered expected prices; label as "farmer estimate" |
| **Future** | Official market statistics, cooperative data, or partner feeds |

---

## 6. Data Quality Status Legend

| Status | Meaning |
|---|---|
| `AVAILABLE` | Data retrieved, quality-checked, and valid for the requested period |
| `STALE` | Data exists but is older than the expected freshness threshold |
| `PARTIAL` | Some variables or time periods are missing within the requested range |
| `MISSING` | No data available for this source/period |
| `LOW_QUALITY` | Data exists but quality flags indicate potential issues |
| `NOT_INTEGRATED` | Data source exists but is not yet connected in this version |

---

## 7. Data Category Labels

| Category | Meaning | Example |
|---|---|---|
| `REMOTE_SENSING_RETRIEVAL` | Product-specific satellite retrieval; use only for a documented retrieval product/variable | A verified satellite retrieval product; classification depends on the exact product |
| `REANALYSIS_OR_ASSIMILATION_ESTIMATE` | Meteorological estimate from assimilation/reanalysis | NASA POWER meteorology sourced from MERRA-2/GEOS-IT |
| `MODELLED_ESTIMATE` | Model-derived spatial product or model-assimilation output | SoilGrids predictions; SMAP L4 |
| `GROUND_MEASURED` | Direct station or laboratory measurement | Weather station; laboratory soil test |
| `USER_PROVIDED` | Farmer-entered value | Soil test result, crop history, priorities |
| `DERIVED` | Calculated from other values | Seasonal mean, anomaly, gauge score |
| `SCENARIO` | Hypothetical future simulation | "What if rainfall decreases 15%?" |

The `data_category` is assigned at parameter/product level, alongside the exact dataset, product/version, parameter, and derivation. GPM IMERG is a satellite-derived precipitation retrieval product rather than a ground rain-gauge observation. A direct laboratory test can be `GROUND_MEASURED`; when entered by a farmer, retain `USER_PROVIDED` as the record provenance and identify the claimed measurement method separately.

## 8. Additional Datasets Referenced by the Master Handoff (P2 / Not Integrated)

The entries below document possible future use only. Mention here does not mean the source is integrated or selected for the MVP. Verify exact collection, version, native support, access, units, and quality rules before implementation.

| Dataset/product family | Intended use | Native support caveat | Limitation and deferral | Official documentation |
|---|---|---|---|---|
| Landsat surface reflectance / vegetation indices | Field-scale vegetation dynamics where field size and valid pixels permit | Product and collection dependent; commonly tens-of-meters pixels; cloud and revisit gaps matter | P2; requires collection/QA selection, compositing, and area coverage checks; greenness does not prove crop identity or farmer action | [USGS Landsat missions](https://www.usgs.gov/landsat-missions) |
| MODIS MOD13 vegetation indices | Regional/seasonal vegetation pattern context | MOD13Q1 is a 16-day, 250 m product (collection/version must be verified) | P2; often too coarse for small farms; compositing and QA required | [NASA MODIS vegetation indices](https://modis.gsfc.nasa.gov/data/dataprod/mod13.php) |
| GRACE / GRACE-FO | Large-scale groundwater/total-water-storage context | Regional mascon or gridded support, far coarser than a farm | P2; cannot support field-level water claims | [NASA GRACE](https://grace.jpl.nasa.gov/data/get-data/) |
| SRTM elevation | Terrain, slope, and relative runoff/erosion context | DEM pixel support and void/processing characteristics vary by product | P2; slope alone does not estimate erosion rate | [NASA SRTM](https://www.earthdata.nasa.gov/data/instruments/srtm) |
| GEDI | Sampled canopy structure/biomass context where relevant | Footprint samples, not wall-to-wall coverage | P2; sampling gaps and product interpretation make it unsuitable as a universal field layer | [NASA GEDI](https://gedi.umd.edu/data/) |

## 9. Data Completeness and Confidence

These are separate concepts. `data_completeness` describes required input/data coverage present divided by the applicable required checks. Its required-check list, denominator, and weighting policy are not yet approved; return `NOT_ASSESSED` with a reason until they are. If later approved, include the numerator, denominator, and method version. `confidence` describes evidence quality and suitability for a particular claim/recommendation; it must not be copied from completeness or inferred from it. Until a defensible rubric is approved, return `NOT_ASSESSED` plus explanatory factors rather than an invented numeric/ordinal confidence.

---

## 10. Verification Checklist (Before Displaying Any Data)

- [ ] Is the product/version documented?
- [ ] Are the units correct and explicitly stored?
- [ ] Is the time standard documented (UTC vs. local)?
- [ ] Is the spatial resolution/support stated?
- [ ] Are quality flags applied?
- [ ] Are missing values handled (not treated as zero)?
- [ ] Is the source-aware data category labeled (retrieval/reanalysis or assimilation/modelled/ground-measured/user-provided/derived/scenario)?
- [ ] Is the retrieval date recorded?
- [ ] Is there a limitation note for the user?
- [ ] Can the value be traced back to its source?

---

## 11. References

1. NASA POWER Daily API — https://power.larc.nasa.gov/docs/services/api/temporal/daily/
2. NASA POWER Temporal APIs — https://power.larc.nasa.gov/docs/services/api/temporal/
3. NASA POWER Data Latency FAQ — https://power.larc.nasa.gov/docs/faqs/data/
4. NASA GPM IMERG Overview — https://gpm.nasa.gov/data/imerg
5. NASA GPM Data Directory — https://gpm.nasa.gov/data/directory
6. NSIDC SMAP Overview — https://nsidc.org/data/smap
7. NSIDC SMAP SPL3SMP_E V6 — https://nsidc.org/data/spl3smp_e/versions/6
8. ECOSTRESS Product Specification — https://ecostress.jpl.nasa.gov/data/product-specification-documents-table
9. NASA AppEEARS — https://appeears.earthdatacloud.nasa.gov/
10. ISRIC SoilGrids — https://isric.org/explore/soilgrids
11. ISRIC SoilGrids Documentation — https://docs.isric.org/globaldata/soilgrids/
12. NASA POWER Meteorological Data Sources — https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
13. NASA POWER Data Sources FAQ — https://power.larc.nasa.gov/docs/faqs/data/
14. NASA POWER Methodology — https://power.larc.nasa.gov/docs/methodology/


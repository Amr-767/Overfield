# Overfield — Data Provenance Registry

**Last updated:** 2026-11-13
**Status:** Phase 4 — NASA POWER is the only integrated provider; all other datasets in the NASA Space Apps 2026 guide are evaluated but not integrated.

---

## Purpose

This document records every data source used in Overfield: the exact product, variables, units, spatial/temporal support, access method, quality flags, processing steps, known limitations, and retrieval dates.

**Every number displayed to a user must be traceable to an entry in this registry.**

**Integration status (2026-11-13).** Only **NASA POWER** is integrated: it has a provider adapter,
catalogue rows, stored observations, and verified API read-back. GPM IMERG, SMAP, Landsat,
Sentinel-2, HLS, MODIS/VIIRS, ECOSTRESS, SRTM, GLDAS, ERA5/ERA5-Land, GAEZ v5 and GEDI were evaluated
and are **not integrated**. U.S.-only resources are not suitable for Gharbia. The full product/version,
resolution, access and classification record is
[`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md).

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
| **Time Standard** | The Daily API defaults to Local Solar Time (LST). The implemented convention is UTC: every request sends `time-standard=UTC` and the client asserts the response echoes UTC; both the requested and returned convention are persisted with the record. |

### Source classification and parameter provenance

POWER is an API/distribution service over multiple source products, not a single observation type. Meteorological parameters originate from assimilation/reanalysis products including MERRA-2 and GEOS-IT. Solar parameters are inferred from satellite observations using radiative-transfer methods. Classification is set per parameter/product from verified product documentation and the response's `x-data-sources` header; POWER data is never labelled as a direct observation. The parameters below are the implemented set.

Official references: [POWER meteorological sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/), [POWER data sources FAQ](https://power.larc.nasa.gov/docs/faqs/data/), [POWER methodology](https://power.larc.nasa.gov/docs/methodology/).

### Implemented Variables (verified 2026-11-09)

| Parameter Code | Meaning | Unit | Overfield Use |
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
- Parameter availability, units and community were verified against the live API on 2026-11-09; re-verify if the requested parameter set changes.

### Processing Steps (implemented in Phase 3B–3E)

1. Request daily data for the farm's representative point and specified date range with explicit `time-standard=UTC`
2. Parse JSON response; validate parameter keys, units, and echoed time standard
3. Handle missing values and fill/sentinel values per POWER documentation (`-999`/`null` → `None`)
4. Store as `EnvironmentalObservation` records with source metadata and provenance
5. Expose daily values through the REST API; Phase 4 indicators aggregate on demand (no snapshot table)

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

## 2. NASA GPM IMERG — Precipitation Estimates (Evaluated, Not Integrated)

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
| **Integration status** | **Not integrated** — evaluated for Phase 5 (regional cross-check only) |

### Candidate Variables

| Variable | Unit | Overfield Use |
|---|---|---|
| Precipitation rate / accumulation | mm/hr or mm | Rainfall totals, dry-spell counts, seasonal anomalies, heavy-rain events |

### Important Limitations

- Satellite precipitation estimates, not rain gauge measurements
- Biases possible in mountainous terrain, coastlines, intense convection
- Early/Late runs are provisional; Final is gauge-adjusted but lags ~3.5 months
- Must convert rates to accumulations correctly (rate × time interval)
- 0.1° (≈11 km) pixel may cover many farms; not a field-level measurement
- Rainfall is not irrigation-water availability (no canal, groundwater, storage or efficiency data)

### Access Method

- GES DISC / NASA Earthdata (HDF5), or Google Earth Engine
- NASA Earthdata Login required for most access paths

### Integration Priority

**Deferred to Phase 5 (P2).** NASA POWER precipitation (`PRECTOTCORR`) remains the Phase 4 source.
IMERG is a regional cross-check candidate only; it must not be blended into WATER without a documented
source-precedence and run-type/version contract.

### Retrieval Date

Not retrieved. No adapter, catalogue rows, or observations exist.

---

## 3. NASA SMAP — Soil Moisture Context (Evaluated, Not Integrated)

| Field | Value |
|---|---|
| **Provider** | NASA / NSIDC DAAC |
| **Products** | L3 `SPL3SMP` v9 (36 km, daily); L4 `SPL4SMGP` (9 km, 3-hourly, model assimilation) |
| **Documentation** | [NSIDC SMAP overview](https://nsidc.org/data/smap), [SPL3SMP v9](https://nsidc.org/data/spl3smp) |
| **Spatial Resolution** | 36 km (L3) / 9 km (L4) EASE-Grid 2.0 |
| **Temporal Resolution** | Daily (L3) / 3-hourly (L4) |
| **Variable** | Surface soil moisture (volumetric water content, m³/m³); L4 adds surface and root-zone moisture |
| **Authentication** | NASA Earthdata Login required |
| **Integration status** | **Not integrated** — Phase 5 candidate (regional context only) |

### Important Limitations

- 9–36 km pixels contain many farms and land-cover types
- L3 is a **surface** estimate (~top 5 cm); L4 adds model-assimilated root-zone moisture
- L4 is model assimilation, not direct retrieval
- Vegetation, frozen ground, water bodies affect the signal
- **Not soil composition** — it does not measure texture, pH, organic carbon, N/P/K, salinity or nutrients
- Cannot prove individual farmer irrigation from SMAP alone

### Integration Priority

**Deferred to Phase 5 (P2).** Regional moisture context only. The Phase 4 SOIL indicator remains based on
`FarmerContext` measurements and must never substitute SMAP moisture for a laboratory soil test.

### Retrieval Date

Not retrieved. No adapter, catalogue rows, or observations exist.

---

## 4. NASA ECOSTRESS — Thermal/ET Context (Evaluated, Not Integrated)

| Field | Value |
|---|---|
| **Provider** | NASA / LP DAAC |
| **Products** | L2G LST&E v002; ECO3ET / ECO3ESI products (verify current versions before implementation) |
| **Documentation** | [Product spec table](https://ecostress.jpl.nasa.gov/data/product-specification-documents-table), [Data resources](https://nasa.github.io/ECOSTRESS-Data-Resources/) |
| **Spatial Resolution** | 70 m for L2G LST&E (product-specific for ET/ESI) |
| **Temporal Resolution** | Irregular (ISS orbit-dependent); ~1–5 day average at varying times, not daily |
| **Authentication** | NASA Earthdata Login required |
| **Access Method** | AppEEARS for area/point subsetting |
| **Integration status** | **Not integrated** — Phase 5 candidate (opportunistic) |

### Important Limitations

- Land-surface temperature ≠ 2-m air temperature; no direct comparison with `T2M_MAX` thresholds
- Irregular revisit — data gaps are normal; acquisitions are not guaranteed for a given farm
- Cloud cover eliminates observations
- ET/ESI are model-derived estimates, not direct water-use measurements
- Product-specific quality flags and units must be applied
- Missing overpass ≠ zero stress

### Integration Priority

**Deferred to Phase 5 (P4).** Opportunistic only, when a valid acquisition intersects the farm. Missing
data must not block the app or be replaced with a synthetic value.

### Retrieval Date

Not retrieved. No adapter, catalogue rows, or observations exist.

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
| **Primary source** | Farmer-entered soil test results (`FarmerContext`) |
| **Evaluated fallback** | SoilGrids 250 m modelled estimates — **not integrated**; Phase 4 SOIL uses `FarmerContext` only |
| **SoilGrids docs** | [ISRIC SoilGrids](https://isric.org/explore/soilgrids) |
| **Required fields** | Texture class, pH, organic carbon, sampling depth, method, date |
| **Limitation** | SoilGrids values are spatial predictions with prediction intervals — not direct field samples, and no fallback value is fabricated when a farmer has no soil data |

### 5.3 Market Prices

| Field | Value |
|---|---|
| **Status** | **UNAVAILABLE** — no verified local farm-gate source (decision R18) |
| **Indicator behaviour** | `MARKET` returns `status: UNAVAILABLE`, no measurements, no synthetic or demo prices |
| **Verified national references (context only, NOT ingested)** | FAOSTAT producer prices, Egypt — annual 1991–2025, `LCU/tonne`, `SLC/tonne`, `USD/tonne`, PPI (2014-2016=100); WFP Egypt food prices — 2010-08-15 → 2026-09-15, EGP retail, national average + Cairo, consumer units |
| **Access notes (verified 2026-11-09)** | FAOSTAT API `fenixservices.fao.org/faostat/api/v1/…` returned **521**; `faostatservices.fao.org` returned **401**; FAOSTAT bulk zips work (`Prices_E_All_Data_(Normalized).zip`, 11.7 MB). HDX API works; both Egypt datasets are CC BY-IGO |
| **Why not used** | National aggregates are not local farm-gate prices; consumer units are not per-tonne; annual producer prices are lagged; the demo region was only confirmed in Phase 4A |
| **Future** | A team-approved regional/cooperative source with documented licence and unit semantics |

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

## 8. Evaluated Datasets Not Integrated (NASA Space Apps 2026 Guide)

The entries below were reviewed for coverage, resolution, access and scientific role. **None is
integrated.** Mention here does not mean the source is selected for the MVP. Full product/version,
spatial/temporal resolution, access method and classification are in
[`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md).

| Dataset/product family | Reviewed role | Native support caveat | Decision | Official documentation |
|---|---|---|---|---|
| Landsat Collection 2 Level-2 | Field/zone vegetation and long baseline | 30 m; 16-day per satellite; cloud/QA masking required | Phase 5 candidate (P1); not integrated | [USGS Landsat](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance) |
| Sentinel-2 MSI Level-2A | Field/zone vegetation; best small-field optical option | 10/20/60 m; 5-day; cloud/`SCL` masking required | Phase 5 candidate (P1); not integrated | [ESA Sentinel-2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) |
| Harmonized Landsat-Sentinel (HLS) | Harmonized 30 m vegetation time series | ~2–3 day combined; cloud/QA masking; data volume | Phase 5 candidate; alternative to separate S2/Landsat | [HLS HLSL30](https://lpdaac.usgs.gov/products/hlsl30v002/) |
| MODIS / VIIRS vegetation indices | Regional/seasonal vegetation context | 250–500 m; 16-day composites; QA required | Phase 5 candidate (regional); not integrated | [MODIS MOD13](https://modis.gsfc.nasa.gov/data/dataprod/mod13.php) |
| SRTM elevation | Terrain, slope, runoff/erosion screening | 30/90 m; static 2000; voids; flat Delta limits value | Later phase; not integrated | [NASA SRTM](https://www.earthdata.nasa.gov/data/instruments/srtm) |
| GLDAS-2.1 | Regional land-surface/climate baseline | 0.25°; model/assimilation; coarse | Later phase; not integrated | [GLDAS](https://ldas.gsfc.nasa.gov/gldas) |
| ERA5 / ERA5-Land | Historical climate/ET0 baseline | 0.25° / 0.1°; reanalysis; coarse | Later phase; not integrated | [ECMWF ERA5](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5) |
| GAEZ v5 | Crop-suitability prior | 30 arc-sec key outputs; model-derived; not current condition | Phase 5 candidate (P3); not integrated | [FAO GAEZ](https://www.fao.org/gaez/en) |
| GEDI | Sampled canopy/biomass context | 25 m footprints, not wall-to-wall; sparse sampling | Not suitable for annual-crop monitoring; not integrated | [NASA GEDI](https://gedi.umd.edu/data/products/) |
| GRACE / GRACE-FO | Large-scale groundwater/total-water-storage context | Regional support, far coarser than a farm | Out of scope for the 2026 audit; not integrated | [NASA GRACE](https://grace.jpl.nasa.gov/data/get-data/) |
| USDA Ag Data Commons | Repository of datasets with varying scope | Coverage is dataset-specific; not a single product | Requires dataset-by-dataset validation; not integrated | [Ag Data Commons](https://agdatacommons.nal.usda.gov/) |

**U.S.-specific resources are not suitable for Gharbia:** Web Soil Survey, SSURGO/STATSGO2, Cropland Data
Layer, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS Market News, NASS QuickStats, OpenET and LANDFIRE.
They must not be integrated as demo or fallback data. In particular, USDA market sources cannot supply
Egyptian farm-gate prices, and U.S. soil surveys cannot supply Egyptian soil composition.

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

## 11. Derived Indicators (Phase 4)

Indicators are **derived** from the sources above; they are not provider products. Each carries a
stable methodology identifier and version in the API response.

| Indicator | Methodology | Inputs | Derived from |
|---|---|---|---|
| WATER | `water.rainfall.v1` (1.0.0) | `PRECTOTCORR` (NASA POWER, MERRA-2) + farmer-reported irrigation context | daily totals over covered days |
| HEAT | `heat.exposure.v1` (1.0.0) | `T2M`, `T2M_MAX`, `T2M_MIN` (NASA POWER, MERRA-2) | daily means/maxima/minima and threshold counts |
| SOIL | `soil.properties.v1` (1.0.0) | `FarmerContext` soil fields (laboratory or farmer-reported) | per-property reporting, no composite score |
| MARKET | `market.unavailable.v1` (1.0.0) | none | `UNAVAILABLE` by decision R18 |

### Source-type distinction

| Type | Example in this project | How it is labelled |
|---|---|---|
| Provider environmental observation | NASA POWER `T2M`, `PRECTOTCORR` | `source: NASA_POWER`, `data_category: REANALYSIS_OR_ASSIMILATION_ESTIMATE` |
| Farmer-reported context | irrigation availability/type/reliability, farmer-entered soil values | `quality: FARMER_REPORTED` |
| Laboratory-tested measurement | soil pH, organic carbon, N/P/K from a lab | `quality: LAB_TEST` (with `lab_name`, `sample_date`, `sampling_method`) |
| Derived indicator | water/heat/soil summaries | `methodology.id` + `version` |
| Unavailable external information | local market prices | `status: UNAVAILABLE`, no measurements |

### What is deliberately not derived

- **No soil moisture, plant-available water, ET deficit, irrigation demand or water stress** — the
  required datasets (SMAP soil moisture, reference ET, irrigation records) are not integrated.
- **No crop-specific heat stress or frost occurrence** — thresholds are generic air-temperature bands;
  crop and growth-stage rules belong to Phase 5.
- **No market prices or trends** — no verified local farm-gate source exists.
- **No climate normals or anomalies** — multi-year backfill is deferred (R19); no period is called a
  normal.

### Thresholds

All indicator thresholds are **project defaults**, configurable via `INDICATOR_*` environment
variables, and are **not** universal agricultural standards. The full list, with meanings, is in
[`ENVIRONMENTAL_INDICATORS.md`](ENVIRONMENTAL_INDICATORS.md) §8.

## 12. References

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
15. Full NASA Space Apps 2026 dataset evaluation — [`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md)


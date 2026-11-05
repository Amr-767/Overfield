# AgroSpace Quest — Data Provenance Registry

**Last updated:** 2026-11-04  
**Status:** Phase 0 — Planning. No data has been fetched yet.

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
| **Spatial Resolution** | Varies by parameter; common grid is 0.5° × 0.5° (~55 km at equator). Exact native resolution depends on the source model/parameter. |
| **Temporal Resolution** | Daily |
| **Temporal Coverage** | 1981 to near-real-time (meteorological latency ~2–3 days; solar ~5–7 days) |
| **Format** | JSON, CSV |
| **Authentication** | None required (public API) |
| **Rate Limits** | Not formally documented; avoid excessive concurrent requests |
| **Time Standard** | Configurable: UTC or LST (local solar time). **We will use UTC and document it.** |

### MVP Variables (to verify against current parameter catalog)

| Parameter Code | Meaning | Unit | AgroSpace Use |
|---|---|---|---|
| `T2M` | Temperature at 2 m | °C | Daily temperature context |
| `T2M_MAX` | Maximum 2-m temperature | °C | Heat exposure summaries |
| `T2M_MIN` | Minimum 2-m temperature | °C | Night-time temperature, frost screening |
| `PRECTOTCORR` | Corrected precipitation | mm/day | Historical rainfall totals and dry-spell detection |
| `RH2M` | Relative humidity at 2 m | % | Humidity context |
| `WS2M` | Wind speed at 2 m | m/s | Optional ET/context inputs |
| `ALLSKY_SFC_SW_DWN` | All-sky surface shortwave downward radiation | MJ/m²/day or kW-hr/m²/day | Solar/radiation context (verify unit) |

### Important Limitations

- **NOT a weather forecast.** POWER provides historical and near-real-time data. Future projections require a separate forecast provider.
- **NOT a field weather station.** Values represent gridded model/reanalysis estimates for a grid cell, not an on-farm sensor.
- **Latency exists.** Recent days may not have data available yet.
- Exact parameter availability, units, and communities should be re-verified against the [POWER Parameter Catalog](https://power.larc.nasa.gov/docs/methodology/) before implementation.

### Processing Steps (planned)

1. Request daily data for farm centroid coordinates, specified date range, UTC time standard
2. Parse JSON response; validate parameter keys and units
3. Handle missing values and fill/sentinel values per POWER documentation
4. Store as `EnvironmentalObservation` records with source metadata
5. Aggregate to seasonal summaries in the indicators layer

### Retrieval Date

Not yet retrieved. Will be recorded on first live fetch.

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

**Candidate for Phase 3 stretch goal.** Only integrate if the team can confidently retrieve, aggregate, and quality-check the data within the available time. NASA POWER precipitation (`PRECTOTCORR`) can serve as an initial rainfall proxy.

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
| `OBSERVED` | Satellite/sensor measurement or retrieval | NASA POWER temperature, GPM rainfall |
| `MODELED_ESTIMATE` | Derived from models with uncertainty | SoilGrids properties, SMAP L4 assimilation |
| `USER_PROVIDED` | Farmer-entered value | Soil test result, crop history, priorities |
| `DERIVED` | Calculated from other values | Seasonal mean, anomaly, gauge score |
| `SCENARIO` | Hypothetical future simulation | "What if rainfall decreases 15%?" |

---

## 8. Verification Checklist (Before Displaying Any Data)

- [ ] Is the product/version documented?
- [ ] Are the units correct and explicitly stored?
- [ ] Is the time standard documented (UTC vs. local)?
- [ ] Is the spatial resolution/support stated?
- [ ] Are quality flags applied?
- [ ] Are missing values handled (not treated as zero)?
- [ ] Is the data category labeled (observed/modeled/user/derived/scenario)?
- [ ] Is the retrieval date recorded?
- [ ] Is there a limitation note for the user?
- [ ] Can the value be traced back to its source?

---

## 9. References

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


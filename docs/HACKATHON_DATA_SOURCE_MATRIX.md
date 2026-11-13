# Overfield — NASA Space Apps 2026 Data Source Matrix

**Last updated:** 2026-11-13
**Status:** Documentation only. **NASA POWER is the only integrated environmental data source.**
**Demonstration region:** Gharbia, Egypt — `EG-GH` (ADR-021)
**Scope:** Phase 4 source scope and Phase 5 planning. This document records what exists, what was evaluated, what is deliberately excluded, and why.

> **Integration evidence rule.** A dataset is "integrated" only when all three exist: a working provider
> adapter, catalogue rows plus stored observations with provenance, and verified read-back through the API.
> Being listed in the NASA Space Apps guide, a handoff document, or this matrix is **not** integration.

---

## 1. Status labels

| Label | Meaning |
|---|---|
| **Integrated** | Working code, catalogue rows, and verified observations exist. |
| **Evaluated, not integrated** | Reviewed against official documentation; no adapter, no stored observations. |
| **Phase 5 candidate** | Plausible after the Phase 5 architectural prerequisites; not approved for implementation. |
| **Later phase** | Context or optional use only; not near-term. |
| **Not suitable for Gharbia** | No Egyptian coverage, or the product cannot support the intended farm-level use. |
| **Requires more validation** | Coverage/quality is dataset-specific and has not been established. |

---

## 2. Integration status at a glance

| Dataset | Current status | Evidence / phase |
|---|---|---|
| **NASA POWER** | **Integrated** | Phase 3B–3E adapter, `DatasetSource` seed, live retrievals recorded in `DATA_PROVENANCE.md`; used by WATER and HEAT |
| GPM IMERG | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate |
| SMAP | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate |
| Landsat Collection 2 | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate |
| Sentinel-2 | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate |
| Harmonized Landsat-Sentinel (HLS) | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate |
| MODIS / VIIRS | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate (regional) |
| ECOSTRESS | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate (opportunistic) |
| SRTM | Evaluated, not integrated | No adapter, no observations; later phase |
| GLDAS-2.1 | Evaluated, not integrated | No adapter, no observations; later phase |
| ERA5 / ERA5-Land | Evaluated, not integrated | No adapter, no observations; later phase |
| GAEZ v5 | Evaluated, not integrated | No adapter, no observations; Phase 5 candidate (crop engine) |
| GEDI | Evaluated, not integrated | No adapter, no observations; not suitable for annual-crop monitoring |
| Web Soil Survey, SSURGO/STATSGO2, CDL, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA AMS, NASS QuickStats, OpenET, LANDFIRE | Not suitable for Gharbia | U.S.-only scope; see §4 |
| USDA Ag Data Commons | Requires more validation | Repository, not a dataset; see §5 |

The active `Provider` catalogue contains **only** `NASA_POWER`; there are no dataset-source rows,
fetch jobs, observations, endpoints, or Celery tasks for any other provider.

---

## 3. Global candidate matrix

Spatial figures are native product resolution, not a claim about farm-level accuracy. "Farm/zone" means
the pixel is small enough that a field can contain multiple pixels; it does not mean the product measures
that field.

| Dataset (provider) | Product / version | Geographic coverage | Spatial / temporal resolution | Variables (units) | Intended agricultural use | Quality and missing-data limitations | Official access | Status |
|---|---|---|---|---|---|---|---|---|
| **NASA POWER** (NASA LaRC) | POWER Daily Point API; MERRA-2 meteorology, CERES SYN1deg solar; API `v2.10.3` verified 2026-11-09 | Global, including EG-GH | MERRA-2 0.5° × 0.625° (≈55 × 69 km); daily | `T2M`, `T2M_MAX`, `T2M_MIN` (°C); `PRECTOTCORR` (mm/day); `RH2M` (%); `WS2M` (m/s); `ALLSKY_SFC_SW_DWN` (MJ/m²/day) | Rainfall/heat context for WATER and HEAT | Reanalysis/assimilation, not on-farm measurement; fill `-999`/`null` → missing; ~2–3 day meteorological latency, ~5–7 day solar latency | REST JSON, `community=AG`, `time-standard=UTC`; no auth | **Integrated** |
| **GPM IMERG V07** (NASA GSFC) | `GPM_3IMERGDF` (Final), `GPM_3IMERGDL` (Late), `GPM_3IMERGDE` (Early) | 60°N–60°S, including EG-GH | 0.1° × 0.1° (≈11 km; ≈10,000 ha per cell); daily, from half-hourly retrievals | Precipitation (mm/day; mm/h at half-hourly) | Regional rainfall cross-check, heavy-rain context; **not** a farm measurement or irrigation supply | Satellite retrieval, not a rain gauge; biases in convection/coast; Early/Late are provisional; Final ~3.5-month latency; one cell covers many farms | GES DISC / Earthdata / GEE; Earthdata login | Evaluated, not integrated — Phase 5 candidate (P2) |
| **SMAP** (NASA / NSIDC) | L3 `SPL3SMP` v9 (radiometer); L4 `SPL4SMGP` (surface + root zone, model assimilation) | 85°N–85°S, including EG-GH | L3 36 km daily; L4 9 km 3-hourly | Surface soil moisture (m³/m³, top ~5 cm); L4 surface and root-zone moisture (model-derived) | Regional surface/root-zone moisture context and anomaly | Coarse; vegetation/frozen ground/water bodies affect retrieval; L4 is model assimilation; **not soil composition**; cannot prove irrigation | NSIDC DAAC / Earthdata; HDF5/EASE-Grid | Evaluated, not integrated — Phase 5 candidate (P2) |
| **Landsat Collection 2** (NASA/USGS) | Landsat 8/9 OLI/TIRS, Collection 2 Level-2 | Global land, including EG-GH | 30 m reflective, 100 m thermal; 16-day per satellite, ~8-day combined | Surface reflectance (unitless), NDVI/EVI (unitless), LST (K) | Field/zone vegetation condition and historical baseline | Cloud/QA masking required; 16-day gaps; mixed pixels; NDVI is not crop identity or nutrient diagnosis | USGS M2M / EarthExplorer / STAC; USGS login for M2M | Evaluated, not integrated — Phase 5 candidate (P1) |
| **Sentinel-2** (ESA/Copernicus) | MSI Level-2A | Global land, including EG-GH | 10/20/60 m; 5-day revisit with S2A + S2B | Surface reflectance (unitless), NDVI/EVI (unitless), Scene Classification Layer | Field/zone vegetation condition; best small-field optical option | Cloud/SCL masking required; mixed pixels at edges; NDVI saturation; no crop identification | Copernicus Data Space Ecosystem / STAC; OAuth | Evaluated, not integrated — Phase 5 candidate (P1) |
| **Harmonized Landsat-Sentinel (HLS)** (NASA LP DAAC) | `HLSL30` v002, `HLSS30` v002 | Global land, including EG-GH | 30 m; ~2–3 day combined revisit | Harmonized surface reflectance, NDVI/EVI (unitless), QA | Consistent long vegetation time series across Landsat and Sentinel-2 | Cloud/QA masking; harmonization assumptions; 30 m mixed pixels; data volume | LP DAAC / AppEEARS / Earthdata | Evaluated, not integrated — Phase 5 candidate (alternative to separate S2 + Landsat) |
| **MODIS / VIIRS** (NASA) | `MOD13Q1` v061, `MYD13Q1` v061; `VNP13A1` v001 | Global, including EG-GH | MODIS 250 m / VIIRS 500 m; 16-day composites | NDVI/EVI (unitless), QA layers | Regional vegetation seasonality and broad anomalies | 250 m pixel = 6.25 ha; mixed land cover; composite/QA handling; too coarse for individual small farms | LP DAAC / AppEEARS; Earthdata login | Evaluated, not integrated — Phase 5 candidate (regional) |
| **ECOSTRESS** (NASA/JPL) | L2G LST&E v002; ECO3ET / ECO3ESI products | Global land, but ISS acquisitions are intermittent over EG-GH | 70 m; irregular ~1–5 day average at varying times; **not daily** | LST (K), emissivity, ET (mm/day), ESI | Opportunistic high-resolution thermal/ET and plant-water-stress context | Non-sun-synchronous; clouds and QA; acquisition gaps; **LST ≠ air temperature**; ET is model-derived | LP DAAC / AppEEARS; Earthdata login | Evaluated, not integrated — Phase 5 candidate (P4) |
| **SRTM** (NASA/USGS) | `SRTMGL1` v003 (1 arc-sec), `SRTMGL3` (3 arc-sec) | 60°N–56°S, including EG-GH | 30 m / 90 m; static (acquired February 2000) | Elevation (m), derived slope/terrain | Terrain, drainage and erosion screening | Voids; 2000 surface; flat Delta terrain limits slope value; elevation is not erosion measurement | USGS / Earthdata | Evaluated, not integrated — later phase |
| **GLDAS-2.1** (NASA GSFC) | GLDAS-2.1 | Global, including EG-GH | 0.25° (≈28 km); 3-hourly and monthly; 2000–present | Soil moisture (kg/m²), ET, runoff, snow | Regional land-surface/climate baseline | Model/assimilation; coarse; duplicates SMAP L4/ERA5 roles; not a farm measurement | GES DISC / Earthdata; NetCDF | Evaluated, not integrated — later phase |
| **ERA5 / ERA5-Land** (ECMWF/C3S) | ERA5; ERA5-Land | Global, including EG-GH | ERA5 0.25° (≈28 km) hourly, 1940–present; ERA5-Land 0.1° (≈9 km) hourly, 1950–present | 2 m temperature, precipitation, radiation, wind, ET0 inputs | Historical climate/ET0 baseline and seasonal context | Reanalysis, not measurement; coarse; latency; duplicates POWER’s role | Copernicus CDS API; ECMWF account + licence | Evaluated, not integrated — later phase |
| **GAEZ v5** (FAO/IIASA) | GAEZ v5 | Global, including EG-GH | 30 arc-sec (≈1 km) for key outputs; 5 arc-min full layers; static/periodic releases | Crop suitability classes, attainable yield, agro-ecological constraints | Crop-suitability prior for future recommendation logic | Model-derived suitability, not current field condition or observed yield; no field-specific guarantee | FAO GAEZ portal / bulk download | Evaluated, not integrated — Phase 5 candidate (P3) |
| **GEDI** (NASA/UMD) | L2 footprint, L3 gridded, L4A/L4B biomass | 51.6°N–51.6°S, including EG-GH geographically | 25 m footprints; 1 km grids; sparse along-track sampling | Canopy height, LAI, above-ground biomass | Orchard/agroforestry/biomass context only | Sparse samples, not wall-to-wall; forest-structure orientation; unsuitable for annual-crop field monitoring | ORNL DAAC / LP DAAC; Earthdata login | Evaluated, not integrated — **not suitable for annual-crop monitoring** |

### 3.1 GPM IMERG — detailed assessment

- **Coverage:** 60°N–60°S, so Gharbia is inside the product domain.
- **Resolution:** 0.1° ≈ 11 km; a single cell is roughly 10,000 ha. It cannot resolve a Gharbia field.
- **Runs:** Early (~4 h), Late (~12–14 h), Final (~3.5 months, gauge-adjusted). Provisional and final
  values must never be mixed without a label.
- **Use:** regional rainfall cross-check against POWER `PRECTOTCORR`, heavy-rain event context, and
  seasonal anomaly. **Not** irrigation-water availability.
- **Why not Phase 4:** it duplicates POWER precipitation at a different grid and adds a second access
  path, QA regime, and run-type/version problem before the indicator contract has a source-precedence rule.

### 3.2 SMAP — detailed assessment

- **L3 `SPL3SMP` v9:** 36 km, daily, 2015-03-31–present, top ~5 cm surface soil moisture.
- **L4 `SPL4SMGP`:** 9 km, 3-hourly, surface and root-zone moisture produced by assimilating SMAP
  brightness temperatures into a land-surface model.
- **Use:** regional moisture context and anomaly.
- **Not equivalent to a laboratory soil test:** it measures volumetric moisture, not texture, pH,
  organic carbon, N/P/K, salinity, or nutrient availability. It does not prove irrigation occurred.
- **Why not Phase 4:** 9–36 km is far larger than a Gharbia farm; the SOIL indicator is intentionally
  based on `FarmerContext`, and adding SMAP would misrepresent moisture as soil composition.

### 3.3 Landsat, Sentinel-2 and HLS — detailed assessment

- **Sentinel-2** is the best field-scale option: 10 m pixels (≈100 per hectare), 5-day revisit with two
  satellites. Cloud masking (`SCL`) and gap handling are mandatory.
- **Landsat Collection 2** provides a long archive at 30 m (≈11 pixels per hectare) and an independent
  historical baseline, but has 16-day gaps and more cloud loss.
- **HLS** harmonizes Landsat and Sentinel-2 to 30 m with ~2–3 day combined revisit; it is an alternative
  architecture, not an additional independent measurement. Choose **one** vegetation architecture.
- **NDVI/EVI** describe vegetation condition/greenness. They are not crop identification, nutrient
  diagnosis, soil health, or a direct measurement of yield.

### 3.4 ECOSTRESS — detailed assessment

- 70 m LST/ET is much finer than POWER or SMAP, but ECOSTRESS is on the ISS, is non-sun-synchronous, and
  acquires a given site only every few days at varying times. It is not a daily product.
- **LST is surface-skin temperature at overpass time**, not 2 m air temperature. It must not be compared
  directly with `T2M_MAX` thresholds without an explicit, validated transformation.
- ET/ESI products are model-derived estimates, not direct water-use measurements.
- Missing acquisitions are normal and must never block the dashboard or be replaced with a synthetic value.

### 3.5 GAEZ v5 — detailed assessment

- GAEZ is an agro-ecological zoning model, not an observation system. It combines climate, soil, terrain
  and crop parameters into suitability classes and attainable-yield estimates.
- It is appropriate as a **prior** for future crop recommendation, clearly labelled model-derived.
- It is **not** a field-specific guarantee of yield and **not** a statement of current field condition.

### 3.6 ERA5 and GLDAS — detailed assessment

- Both are reanalysis/model products, not farm measurements. ERA5-Land (0.1°) is finer than ERA5
  (0.25°) and GLDAS-2.1 (0.25°), but all remain regional.
- Their value is historical climate/ET0 context, not current field state.
- They overlap POWER’s role; if one is added, it must be a labelled baseline layer, not an additional
  “independent” measurement of the same signal.

---

## 4. Geographically unsuitable resources

These resources appear in the challenge guide but do **not** cover Gharbia. They must not be integrated
as demo or fallback data.

| Resource | Provider | Published scope | Why it is not suitable for Gharbia | Status |
|---|---|---|---|---|
| **Web Soil Survey (WSS)** | USDA NRCS | United States and territories | No Egyptian soil map units or survey data | **Not suitable for Gharbia** |
| **SSURGO / STATSGO2** | USDA NRCS | United States | National soil survey; no Egyptian coverage | **Not suitable for Gharbia** |
| **Cropland Data Layer (CDL)** | USDA NASS | Conterminous United States | U.S. crop-specific land cover only | **Not suitable for Gharbia** |
| **PRISM** | Oregon State University / PRISM Climate Group | Conterminous U.S. (separate Alaska/Hawaii/Puerto Rico products) | U.S. gridded climate, not Egypt | **Not suitable for Gharbia** |
| **NAIP** | USDA | Conterminous United States | U.S. aerial imagery only | **Not suitable for Gharbia** |
| **NLCD** | USGS / MRLC | United States | U.S. land cover only | **Not suitable for Gharbia** |
| **CoCoRaHS** | Community volunteer network | United States / Canada | No Egyptian station network | **Not suitable for Gharbia** |
| **NWIS** | USGS | United States | U.S. water data only | **Not suitable for Gharbia** |
| **USDA AMS Market News** | USDA | United States | U.S. market reporting; cannot supply Egyptian farm-gate prices | **Not suitable for Gharbia** |
| **NASS QuickStats** | USDA | United States | U.S. agricultural statistics only | **Not suitable for Gharbia** |
| **OpenET** | NASA / DRI / EDF consortium | 23 western U.S. states (plus Mississippi Alluvial Plain rasters) | Operational coverage is U.S.-only; global expansion is stated intent, not current coverage | **Not suitable for Gharbia** |
| **LANDFIRE** | US DOI / USFS | United States | U.S. fire/fuel/vegetation layers only | **Not suitable for Gharbia** |

**Market consequence:** USDA AMS and NASS cannot fill the Egyptian farm-gate price gap. MARKET remains
`UNAVAILABLE` (decision R18) until a verified local/regional Egyptian source is approved.

**Soil consequence:** WSS/SSURGO/STATSGO2 cannot supply Egyptian soil composition. SOIL remains based on
`FarmerContext` measurements and provenance, never on a U.S. soil survey.

---

## 5. USDA Ag Data Commons — dataset-by-dataset evaluation

Ag Data Commons is a **USDA National Agricultural Library repository**, not a single geospatial dataset.
Its holdings have different geographic extents, resolutions, licences and update rules. A blanket claim
that "Ag Data Commons covers Egypt" would be false, and a blanket rejection of every hosted dataset would
be equally unjustified.

**Decision:** no individual Ag Data Commons dataset is selected, integrated, or planned. The repository
is classified **Requires more validation**.

Any future candidate must pass this checklist before it can enter the catalogue:

| Check | Requirement |
|---|---|
| Geographic coverage | Explicitly includes Egypt / the Nile Delta, or is global with Egyptian validity |
| Spatial support | Suitable for the intended use (farm/zone vs regional context) |
| Temporal coverage | Includes the period needed; update cadence documented |
| Variables and units | Exact variable definitions, units, and derivation method documented |
| Quality and missing data | QA flags, fill values, and known gaps documented |
| Licence and attribution | Compatible with the project; attribution text recorded |
| Access | Stable official access method; authentication requirements known |
| Scientific role | Clearly separated from observed farm conditions and from other sources |

Until a specific dataset passes all checks, it must not appear as an integrated source or as a fallback.

---

## 6. Scientific distinctions that must survive integration

These are non-negotiable interpretation rules, regardless of which Phase 5 dataset is added.

### 6.1 SMAP moisture is not a soil laboratory measurement

SMAP estimates volumetric surface moisture (L3) or model-assimilated surface/root-zone moisture (L4).
It does not measure texture, pH, organic carbon, nitrogen, phosphorus, potassium, salinity, or nutrient
availability. It cannot replace a soil test and cannot prove that a farmer irrigated.

### 6.2 ECOSTRESS surface temperature is not air temperature

ECOSTRESS LST is the temperature of the surface skin at an overpass time. It is not the 2 m air
temperature reported by POWER, and it is not interchangeable with `T2M_MAX`. Any comparison requires an
explicit, validated transformation and separate interpretation.

### 6.3 GPM rainfall is not irrigation-water availability

GPM estimates precipitation. It does not measure canal delivery, groundwater, stored water, irrigation
efficiency, or whether a farmer can irrigate. A rainfall total must never be presented as water supply
or irrigation adequacy.

### 6.4 NDVI/EVI vegetation condition is not soil health

NDVI/EVI are optical greenness indices. They respond to vegetation cover and condition, not to soil
organic matter, nutrients, salinity, texture, or biological activity. They are affected by clouds,
mixed pixels, soil background, saturation, and crop stage.

### 6.5 GAEZ suitability is not a field-specific yield guarantee

GAEZ is a model-derived agro-ecological suitability product. It can inform a crop-suitability prior, but
it does not describe current field conditions and does not guarantee yield. Any use must be labelled as
model-derived and separated from observed farm data.

### 6.6 Reanalysis is not measurement

POWER/MERRA-2, ERA5, ERA5-Land and GLDAS are reanalysis or model-assimilation products. They are
legitimate regional estimates, not on-farm sensors. This distinction must remain visible in the API and UI.

---

## 7. Spatial reality check

| Source | Cell/pixel size | Hectares per pixel | Pixels in a 1 ha field |
|---|---|---|---|
| MERRA-2 (POWER) | 0.5° × 0.625° | ≈330,000 ha | ≪ 1 |
| IMERG | 0.1° | ≈10,000 ha | ≪ 1 |
| SMAP L3 | 36 km | ≈130,000 ha | ≪ 1 |
| SMAP L4 | 9 km | ≈8,100 ha | ≪ 1 |
| ERA5 / GLDAS | 0.25° | ≈66,000 ha | ≪ 1 |
| ERA5-Land | 0.1° | ≈10,000 ha | ≪ 1 |
| MODIS | 250 m | 6.25 ha | 0.16 |
| ECOSTRESS | 70 m | 0.49 ha | ≈2 |
| Landsat | 30 m | 0.09 ha | ≈11 |
| Sentinel-2 | 10 m | 0.01 ha | ≈100 |

Many Egyptian holdings are around a feddan (≈0.42 ha) and are often fragmented; the exact distribution
should be confirmed from Egyptian agricultural statistics before any spatial claim is made. The structural
point is that anything coarser than ~30 m cannot describe an individual Gharbia field.

---

## 8. Architecture implications

### Current Phase 4 capabilities

- A per-farm, daily scalar time series (`EnvironmentalObservation`) with provenance.
- Strict missing-data handling (`MISSING` + `NULL`, never zero).
- Catalogue metadata per parameter (units, product, category, native-resolution note).
- Idempotent `(farm, source, observation_date)` storage.
- Indicator contract with coverage, confidence and freshness.

### Gaps that block raster/area sources

1. No raster or polygon zonal-statistics path.
2. Quality is only `AVAILABLE`/`MISSING`; no cloud/QA/retrieval-failure reason.
3. `(farm, source, date)` uniqueness blocks multiple runs/versions or overpasses per day.
4. `DataFetchJob` is farm-scoped; a scene covers many farms.
5. `TemporalResolution` only expresses daily data.
6. No source-precedence or duplicate policy.
7. No per-observation valid-pixel count or aggregation method.

### Phase 5 prerequisites (planning only)

- Add provider values and `DatasetSource` seeds.
- Extend observation metadata for QA, pixel count/coverage, aggregation method, and product run/version.
- Add a scene/collection job or shared cache.
- Add raster ingestion and zonal statistics (GDAL/rasterio or an external service).
- Define source precedence before storing a second source for the same signal.
- Add cadence-aware refresh and per-source freshness policies.
- Keep `score` null until a crop-aware rubric is approved.

**Phase 4 does not change.** The current point-based POWER implementation and indicator methodology remain
the approved baseline.

---

## 9. Recommended source priority

| Priority | Source | Role | Timing |
|---|---|---|---|
| P0 | NASA POWER | WATER + HEAT; only Phase 4 source | Integrated |
| P1 | Sentinel-2 L2A NDVI/EVI | Field/zone vegetation condition | First Phase 5 integration |
| P1 | Landsat C2 L2 NDVI/EVI **or** HLS | Long baseline / harmonized time series | Choose one architecture alongside Sentinel-2 |
| P2 | GPM IMERG Final V07 | Regional rainfall cross-check | After vegetation is stable |
| P2 | SMAP L4 9 km | Regional moisture context | After a validation spike |
| P3 | ERA5-Land or GLDAS-2.1 (one) | Climate/ET0 baseline | Only if a historical-baseline feature is approved |
| P3 | GAEZ v5 | Crop-suitability prior | With future crop-recommendation logic |
| P4 | ECOSTRESS | Opportunistic LST/ET context | Only when valid coverage is verified |
| P4 | SRTM | Terrain/erosion screening | Only if a terrain feature is approved |
| P5 | GEDI | Orchard/agroforestry biomass context | Only for a specific woody-biomass question |
| Never | U.S.-only resources, OpenET | — | Do not integrate |

---

## 10. Explicit decisions

1. **Do not integrate** Web Soil Survey, SSURGO/STATSGO2, CDL, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, USDA
   AMS Market News, NASS QuickStats, OpenET, or LANDFIRE: they do not cover Gharbia.
2. **Do not integrate GEDI** for annual-crop field monitoring: it is a sparse footprint sample, not a
   wall-to-wall crop layer.
3. **Do not treat Ag Data Commons as a source.** Evaluate individual datasets only; none is selected today.
4. **Do not use SMAP as soil composition**, or any satellite product as a substitute for a laboratory soil test.
5. **Do not use USDA market data** as Egyptian farm-gate prices. MARKET stays `UNAVAILABLE`.
6. **Do not add IMERG to WATER in Phase 4.** A second precipitation source requires a source-precedence
   contract and run-type/version handling.
7. **Do not fabricate fallback values.** Missing data stays missing.

---

## 11. Verification notes

- Repository inspection confirmed that the only provider adapter is NASA POWER and that no
  GPM/SMAP/Landsat/Sentinel/ECOSTRESS/ERA5/GLDAS/GAEZ/SRTM/GEDI code or observations exist.
- Official product pages were consulted on 2026-11-13. Product versions are current as of that date and
  must be re-verified before implementation.
- Not verified in this documentation pass: actual acquisition counts over Gharbia for ECOSTRESS, GEDI,
  Landsat or Sentinel-2; seasonal cloud statistics; Egyptian farm-size distribution; full licence terms;
  exact current versions of every SMAP L4/ECOSTRESS product. These require a read-only Phase 5 validation
  spike before any integration is approved.

---

## 12. References

1. NASA POWER Daily API — https://power.larc.nasa.gov/docs/services/api/temporal/daily/
2. NASA POWER data sources — https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
3. GPM IMERG — https://gpm.nasa.gov/data/imerg
4. GPM IMERG V07 daily product — https://www.earthdata.nasa.gov/dashboard/data-catalog/GPM_3IMERGDF.v07
5. SMAP data products — https://smap.jpl.nasa.gov/data/
6. SMAP L3 `SPL3SMP` v9 — https://nsidc.org/data/spl3smp
7. Landsat Collection 2 — https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance
8. Sentinel-2 — https://sentinel.esa.int/web/sentinel/missions/sentinel-2
9. Harmonized Landsat-Sentinel — https://lpdaac.usgs.gov/products/hlsl30v002/
10. MODIS vegetation indices — https://modis.gsfc.nasa.gov/data/dataprod/mod13.php
11. VIIRS `VNP13A1` — https://lpdaac.usgs.gov/products/vnp13a1v001/
12. ECOSTRESS — https://ecostress.jpl.nasa.gov/
13. ECOSTRESS FAQ — https://ecostress.jpl.nasa.gov/downloads/faq/ECOSTRESS_FAQ_20240401.pdf
14. SRTM — https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1
15. GLDAS — https://ldas.gsfc.nasa.gov/gldas
16. ERA5 — https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5
17. GAEZ v5 — https://www.fao.org/gaez/en
18. GEDI products — https://gedi.umd.edu/data/products/
19. OpenET FAQ (coverage) — https://etdata.org/faqs/
20. USDA Web Soil Survey — https://www.nrcs.usda.gov/resources/data-and-reports/web-soil-survey
21. USDA Cropland Data Layer — https://nassgeodata.gmu.edu/CropScape/
22. PRISM — https://prism.oregonstate.edu/
23. NLCD — https://www.mrlc.gov/
24. CoCoRaHS — https://www.cocorahs.org/
25. USGS NWIS — https://waterdata.usgs.gov/nwis
26. USDA AMS Market News — https://www.ams.usda.gov/market-news
27. USDA NASS QuickStats — https://quickstats.nass.usda.gov/
28. LANDFIRE — https://www.landfire.gov/
29. USDA Ag Data Commons — https://agdatacommons.nal.usda.gov/

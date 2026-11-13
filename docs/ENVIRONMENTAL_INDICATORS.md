# Overfield — Environmental Indicators

**Last updated:** 2026-11-13
**Status:** Phase 4B–4D implemented; this document describes the behaviour that exists in
`backend/apps/indicators/`. Phase 4 uses **NASA POWER only**; all other datasets in the NASA Space Apps
2026 guide are evaluated but not integrated.
**Scope:** the four decision-support indicators (WATER, HEAT, SOIL, MARKET) and the summary endpoint
`GET /api/v1/farms/{farm_id}/environment/current/`.

> **What these indicators are not.** They are transparent summaries of the data the project actually
> holds. They are **not** crop-specific agronomic advice, not a yield forecast, not a water-balance
> model, and not a soil-health score. No 0–100 score is produced in Phase 4 (decision R14).

---

## 1. Shared response contract

Every indicator returns the same envelope (`apps/indicators/contract.py`):

| Field | Meaning |
|---|---|
| `code`, `label` | `WATER`/`Water`, `HEAT`/`Heat`, `SOIL`/`Soil`, `MARKET`/`Market` |
| `status` | `OK`, `PARTIAL`, `INSUFFICIENT_DATA`, `NOT_ASSESSED`, `UNAVAILABLE` |
| `score` | **always `null`** in Phase 4 |
| `confidence` | `NONE`, `LOW`, `MEDIUM`, `HIGH` — coverage-based, capped for grid-cell sources |
| `as_of` | newest observation used (soil: sample date; market: `null`) |
| `period` | `start`, `end`, `latest_observation`, `age_days`, `freshness`; `null` when there is no observation period (market always; soil without a sample date) |
| `coverage` | `days_expected`, `days_covered`, `days_missing`, `ratio`, `by_parameter` (time-series only) |
| `completeness` | `properties_expected`, `properties_present`, `ratio` (soil only) |
| `summary` | one plain-language sentence set |
| `measurements` | physical values with unit, source, parameter, product, quality, method, interpretation |
| `context` | farmer-reported or sampling metadata (never scored) |
| `drivers` | short reasons with a direction (`POSITIVE`/`NEGATIVE`/`NEUTRAL`) |
| `missing` | `name`, `impact`, `required_for` — what could not be assessed |
| `methodology` | `id`, `version`, `description`, `threshold_source` |
| `sources` | provider, parameter, units, product, data category, native resolution note, time standard, access date |
| `limitations` | explicit caveats for that indicator |

**Status rules used by the services**

| Status | Meaning |
|---|---|
| `OK` | every required day/property for that indicator is present |
| `PARTIAL` | some data exists, but days or properties are missing |
| `INSUFFICIENT_DATA` | no usable observation for the indicator |
| `NOT_ASSESSED` | reserved; not emitted in Phase 4 |
| `UNAVAILABLE` | no source exists (market) |

**Confidence bands** (non-overlapping, `apps/indicators/coverage.py`):

| Coverage | Confidence |
|---|---|
| `0 %` | `NONE` |
| `> 0 %` and `< 60 %` | `LOW` |
| `60 %` to `< 95 %` | `MEDIUM` |
| `≥ 95 %` | `HIGH` |

Water and heat are **capped at `MEDIUM`** because the values are MERRA-2 grid-cell estimates, not
field measurements. Soil is not capped (laboratory data can reach `HIGH`).

**Freshness** is reported separately from confidence:

| Age of newest observation | Freshness |
|---|---|
| `≤ 7 days` | `FRESH` |
| `8–30 days` | `RECENT` |
| `> 30 days` | `STALE` |
| no observation | `UNKNOWN` |

Soil uses its own sample-age labels (§5).

---

## 2. Definition of "current"

The endpoint is named `current`, but it does **not** return real-time weather.

1. The newest stored observation date for the farm is found (one aggregate query).
2. The analysis window **ends at that date** and spans `window_days` back (default 30, range 1–366).
3. `window.latest_observation`, `window.age_days` and `window.freshness` expose how old the data is.
4. With no observations, the window ends today and the time-series indicators report
   `INSUFFICIENT_DATA`; no values are invented.

The window applies to **water and heat only**. Soil uses its sample date; market has no observation
period.

**Top-level vs indicator-level age.** The top-level `window.latest_observation` is computed across the
stored POWER catalogue (all active parameters), while each indicator's `period.latest_observation`
reflects the inputs that indicator actually used. The two can differ — for example, if a non-indicator
parameter was fetched on a later date. When input-specific age matters, compare the indicator-level
`period`, not only the top-level freshness.

---

## 3. WATER — `water.rainfall.v1` (1.0.0)

**Source:** NASA POWER Daily Point API, community `AG`, parameter `PRECTOTCORR`
("Precipitation Corrected"), unit **`mm/day`**, product **MERRA-2**, daily **total**, time standard
**UTC**, native grid **0.5° × 0.625°** (MERRA-2). Values are reanalysis/assimilation estimates.

| Measurement | Formula | Unit |
|---|---|---|
| `precipitation_total` | Σ `PRECTOTCORR` over **covered** days only | mm |
| `rainy_days` | count(covered day ≥ `INDICATOR_RAINY_DAY_MM`, default **1.0**) | days |
| `max_daily_rainfall` | max covered daily total | mm |
| `longest_observed_dry_spell` | longest run of covered days `< 1.0 mm` | days |

**Coverage:** `days_expected` = window length; `days_covered` = days with a non-null value;
`days_missing` = difference; `ratio` = covered / expected.

**Missing days are never zero.** A day without an observation is excluded from totals and counts, and
the summary states that the total covers observed days only.

**Dry spells and gaps.** A missing day **interrupts** the run. The reported value is the longest
*observed* consecutive run, and the measurement's `method` records
`contiguity=CONTIGUOUS` or `contiguity=INTERRUPTED_BY_MISSING_DAYS`. If no day is observed, the value
is `null` with `contiguity=UNKNOWN`.

**Status:** `INSUFFICIENT_DATA` when no day is covered; `PARTIAL` when any day is missing; `OK`
otherwise. **Confidence:** coverage band, capped at `MEDIUM`.

**Farmer context (not scored):** `irrigation_available`, `irrigation_type`, `water_reliability` are
returned in `context` with `quality: FARMER_REPORTED`.

**Explicitly missing:** `soil_moisture`, `reference_evapotranspiration`, `irrigation_records`.

> **Limitation:** rainfall is **not** soil moisture, plant-available water, irrigation demand, ET
> deficit or water stress. None of those can be derived from the data the project holds.

---

## 4. HEAT — `heat.exposure.v1` (1.0.0)

**Sources:** `T2M` (daily mean), `T2M_MAX` (daily maximum), `T2M_MIN` (daily minimum), unit **`C`**,
product **MERRA-2**, time standard **UTC**, native grid **0.5° × 0.625°**.

| Measurement | Formula | Unit |
|---|---|---|
| `mean_temperature` | mean of `T2M` over covered days | °C |
| `mean_daily_maximum` | mean of `T2M_MAX` over covered days | °C |
| `mean_daily_minimum` | mean of `T2M_MIN` over covered days | °C |
| `hot_days` | count(`T2M_MAX ≥ INDICATOR_HOT_DAY_C`, default **35**) | days |
| `very_hot_days` | count(`T2M_MAX ≥ INDICATOR_VERY_HOT_DAY_C`, default **40**) | days |
| `cool_nights` | count(`T2M_MIN ≤ INDICATOR_COOL_NIGHT_C`, default **5**) | days |

**Coverage** is the **weakest** of the three parameters; `coverage.by_parameter` keeps the detail.
A count is `null` (not `0`) when its parameter has no observation at all.

**Status:** `INSUFFICIENT_DATA` when none of the three parameters has data; `PARTIAL` when any day or
parameter is missing; `OK` otherwise. **Confidence:** coverage band, capped at `MEDIUM`.

> **Limitations:** these are **air-temperature exposure** metrics at a grid cell. They are **not**
> crop-specific heat stress, and the thresholds are generic project defaults, not universal
> agricultural thresholds. A **cool night is not evidence of frost** — the 5 °C band is a generic
> exposure count, not a frost indicator.

---

## 5. SOIL — `soil.properties.v1` (1.0.0)

**Source:** `FarmerContext` (Phase 2). Provenance is carried per measurement via `soil_source`:
`LAB_TEST`, `FARMER_REPORTED`, `EXTERNAL_PROVIDER`, `REMOTE_SENSING`, `UNKNOWN`.

| Measurement | Unit | Interpretation |
|---|---|---|
| `ph` | pH | descriptive band only: `ACIDIC < 6.0`, `NEUTRAL 6.0–7.5`, `ALKALINE > 7.5` |
| `organic_carbon_percent` | % | reported as measured; no good/bad threshold, no trend from one sample |
| `nitrogen_ppm` / `phosphorus_ppm` / `potassium_ppm` | ppm | method preserved; **never** classified deficient/sufficient/excessive |
| `texture_class` | class | qualitative context; no water-holding capacity derived |

**Context (not scored):** `sample_date`, `sampling_depth_cm`, `sampling_method`, `lab_name`.

**Completeness:** six core properties (`ph`, organic carbon, N, P, K, texture).
`OK` when all six exist, `PARTIAL` when some do (with an explicit `missing[]` list),
`INSUFFICIENT_DATA` when there is no context or no soil property.

**Sample freshness** (operational labels, separate from confidence):

| Sample age | Label |
|---|---|
| `< 12 months` | `FRESH` |
| `12–24 months` | `AGEING` |
| `> 24 months` | `STALE` |
| no sample date | `UNKNOWN` |
| sample date in the future | `FUTURE` (never treated as fresh) |

**Confidence** = completeness × provenance factor × freshness factor, mapped to the shared bands:

| Provenance | Factor | | Freshness | Factor |
|---|---|---|---|---|
| `LAB_TEST` | 1.00 | | `FRESH` | 1.00 |
| `EXTERNAL_PROVIDER` | 0.80 | | `AGEING` | 0.75 |
| `FARMER_REPORTED` | 0.70 | | `STALE` | 0.50 |
| `REMOTE_SENSING` | 0.60 | | `UNKNOWN` | 0.60 |
| `UNKNOWN` | 0.40 | | `FUTURE` | 0.40 |

Example: complete fresh lab sample → `HIGH`; complete fresh farmer-reported → `MEDIUM`; complete stale
lab sample → `LOW`.

> **No composite soil-health score exists.** N/P/K values depend on the laboratory extraction method
> and are not comparable across methods; pH bands are descriptive, not a crop-suitability judgement;
> texture is qualitative; a single sample cannot show a trend.

---

## 6. MARKET — `market.unavailable.v1` (1.0.0)

**Status: `UNAVAILABLE`.** No measurements, no prices, no synthetic or demo values (decision R18).

**Why:** there is no verified **local farm-gate** price source for the demonstration region
(Gharbia, `EG-GH`). The two verified national references are **not** local prices and are **not
integrated**:

| Candidate | Verified nature (2026-11-09) | Why it is not used |
|---|---|---|
| FAOSTAT producer prices (Egypt) | annual, national, `LCU/tonne`, `SLC/tonne`, `USD/tonne`, PPI; 1991–2025 | national annual aggregate, not a local farm-gate price |
| WFP Egypt food prices | ~monthly, national average + Cairo, **retail**, EGP per consumer unit; 2010-08 → 2026-09 | retail consumer units, not farm-gate per tonne |

**Reported instead:** `missing[]` lists `local_market_prices`, `crop_specific_price`, `market_access`,
`expected_yield`; `limitations[]` names the national sources as context only.

**Before MARKET can be enabled:** a documented local/regional price source with licence, currency,
unit (per tonne or per kg), market coverage, observation date and update frequency must be approved;
the region must be confirmed; and unit conversions must be explicit.

---

## 7. Methodology identifiers and versions

| Indicator | Identifier | Version | Implementation |
|---|---|---|---|
| Water | `water.rainfall.v1` | `1.0.0` | `apps/indicators/services/water.py` |
| Heat | `heat.exposure.v1` | `1.0.0` | `apps/indicators/services/heat.py` |
| Soil | `soil.properties.v1` | `1.0.0` | `apps/indicators/services/soil.py` |
| Market | `market.unavailable.v1` | `1.0.0` | `apps/indicators/services/market.py` |

> Note: the Phase 4A prompt suggested `soil.profile.v1` as an example identifier. The implemented
> identifier is **`soil.properties.v1`**; this document records the code, not the example.

## 8. Configurable thresholds

All thresholds are project defaults, configurable through environment variables. **None is a
scientifically established universal agricultural threshold.**

| Setting | Default | Meaning |
|---|---|---|
| `INDICATOR_DEFAULT_WINDOW_DAYS` | `30` | default analysis window |
| `INDICATOR_MAX_WINDOW_DAYS` | `366` | maximum accepted `window_days` |
| `INDICATOR_RAINY_DAY_MM` | `1.0` | rainy-day threshold (mm/day) |
| `INDICATOR_HOT_DAY_C` | `35` | generic hot-day band (°C) |
| `INDICATOR_VERY_HOT_DAY_C` | `40` | generic very-hot-day band (°C) |
| `INDICATOR_COOL_NIGHT_C` | `5` | generic cool-night band (°C) — **not** a frost threshold |
| `INDICATOR_FRESH_MAX_DAYS` | `7` | freshness: `FRESH` up to this age |
| `INDICATOR_RECENT_MAX_DAYS` | `30` | freshness: `RECENT` up to this age |
| `INDICATOR_SOIL_FRESH_MONTHS` | `12` | soil sample `FRESH` below this age |
| `INDICATOR_SOIL_STALE_MONTHS` | `24` | soil sample `STALE` above this age |

---

## 9. Provenance summary

| Data | Type | Label in the API |
|---|---|---|
| NASA POWER `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR` | reanalysis/assimilation estimate (MERRA-2) | `source: NASA_POWER`, `data_category: REANALYSIS_OR_ASSIMILATION_ESTIMATE` |
| NASA POWER `RH2M`, `WS2M` | derived from MERRA-2 + POWER | `data_category: DERIVED` (not used by Phase 4 indicators) |
| NASA POWER `ALLSKY_SFC_SW_DWN` | satellite-derived estimate (CERES SYN1deg) | `data_category: SATELLITE_DERIVED_ESTIMATE` (not used by Phase 4 indicators) |
| Irrigation availability/type/reliability | farmer-reported | `quality: FARMER_REPORTED` |
| Soil properties | laboratory or farmer-reported | `quality: LAB_TEST` / `FARMER_REPORTED` / … |
| Water/heat/soil indicators | derived by this project | `methodology.id` + `version` |
| Market prices | unavailable | `status: UNAVAILABLE` |

Full source metadata (provider, product, parameter, unit, native resolution, time standard, access
date) is in [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md).

---

## 10. Known limitations (all indicators)

1. Environmental values are **grid-cell estimates** for the farm's representative point, not on-farm
   measurements; a farm is a fraction of a MERRA-2 cell.
2. The window ends at the **latest available observation**, not today; stale data is labelled.
3. Missing days are never zero-filled; totals and counts cover observed days only.
4. No crop-specific thresholds, growth stages, soil-moisture, ET or market data are used.
5. No 0–100 scores are produced in Phase 4.
6. No historical backfill or climate normals exist; anomalies are not calculated.

---

## 11. Data-source scope and scientific distinctions

**Only NASA POWER is integrated.** The indicators above are computed exclusively from stored
`EnvironmentalObservation` rows whose provider is `NASA_POWER`, plus `FarmerContext` for SOIL. No GPM,
SMAP, Landsat, Sentinel-2, HLS, MODIS/VIIRS, ECOSTRESS, SRTM, GLDAS, ERA5, GAEZ or GEDI data exists in the
database, and no API response claims otherwise.

Datasets are classified as integrated, evaluated-not-integrated, Phase 5 candidate, later phase, or not
suitable for Gharbia in
[`HACKATHON_DATA_SOURCE_MATRIX.md`](HACKATHON_DATA_SOURCE_MATRIX.md). The following interpretation rules
survive any future integration:

| Tempting substitution | Why it is wrong |
|---|---|
| SMAP moisture → soil laboratory measurement | SMAP estimates volumetric surface moisture (or model-assimilated root-zone moisture at L4). It does not measure texture, pH, organic carbon, N/P/K, salinity or nutrients, and it cannot replace a soil test or prove irrigation. |
| ECOSTRESS LST → air temperature | LST is surface-skin temperature at an overpass time, not 2 m air temperature. It is not interchangeable with `T2M_MAX` and needs an explicit validated transformation. |
| GPM rainfall → irrigation-water availability | Precipitation is not canal delivery, groundwater, storage, irrigation efficiency or a farmer's ability to irrigate. |
| NDVI/EVI → soil health | Greenness responds to vegetation condition, not soil organic matter, nutrients, salinity or texture, and it is affected by clouds, mixed pixels and saturation. |
| GAEZ suitability → field-specific yield | GAEZ is a model-derived agro-ecological suitability product; it does not describe current field condition and does not guarantee yield. |
| POWER/ERA5/GLDAS reanalysis → on-farm measurement | These are gridded reanalysis or model-assimilation estimates, not field sensors. |

**Confidence and freshness are separate.** Confidence describes how much of the expected input was
available and how trustworthy the source class is; freshness describes how old the newest input is. A
complete but old series can be `HIGH` confidence and `STALE`, and neither value is a data-quality
judgement about agronomic suitability.

---

## 12. References

Verified during Phase 3A/4A (2026-11-09):

1. NASA POWER Daily API — https://power.larc.nasa.gov/docs/services/api/temporal/daily/
2. NASA POWER meteorological sources (MERRA-2 0.5° × 0.625°) — https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
3. NASA POWER methodology (CERES SYN1deg) — https://power.larc.nasa.gov/docs/methodology/
4. FAOSTAT producer prices, Egypt (HDX mirror, CC BY-IGO) — https://data.humdata.org/dataset/egypt-food-prices
5. WFP Egypt food prices (HDX, CC BY-IGO) — https://data.humdata.org/dataset/egypt-food-prices
6. FAO GIEWS FPMA — https://fpma.fao.org/giews/food-prices/

No agronomic threshold source is cited because no crop-specific threshold is implemented.

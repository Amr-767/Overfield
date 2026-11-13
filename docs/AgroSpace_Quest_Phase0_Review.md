# Historical Phase 0 Review — Former Project Name: AgroSpace Quest

**Review date:** 2026-11-05
**Historical note:** This review concerns the former AgroSpace Quest project identity; current project status is documented under Overfield.
**Reviewed material:** `PROJECT_STATUS.md`, `DEVELOPMENT_PLAN.md`, `ARCHITECTURE_DECISIONS.md`, `API_CONTRACTS.md`, `DATA_PROVENANCE.md`, plus the Master Agent Handoff and Antigravity Phased Coding Playbook included in the submitted ZIP.

## 1. Verdict

**Phase 0 is substantially drafted, but it is not ready to be marked fully complete yet.**

The team has a useful architecture baseline and a sensible phase sequence. The modular-monolith approach, Django REST Framework, PostgreSQL/PostGIS, Celery/Redis, provider adapters, deterministic crop-rotation logic, and separation of observed/modelled/user-provided/scenario data are reasonable starting decisions for a three-person hackathon team.

However, the status document overstates completion. It says a risk register was created, but the submitted ZIP contains no separate risk register and the development plan does not contain a substantive risk register. There are also specific contradictions and gaps between the master brief, API contracts, architecture decisions, and data provenance registry. These should be corrected before Phase 1 so agents do not implement inconsistent contracts.

**Recommended status: `APPROVED WITH DOCUMENTATION FIXES` — do not begin Phase 1 until the critical fixes in Section 3 are applied.**

This is not a request to redesign the whole system. Most of the work is targeted correction and alignment.

---

## 2. What is already good

1. **A coherent MVP journey exists.** The plan follows a farm-to-context-to-environment-to-rotation-to-simulation flow, rather than building a generic dashboard first.
2. **The scope is sensibly separated.** The plan distinguishes P0, P1, and P2 work and defers multi-country integrations, automated partner workflows, and unsupported satellite verification.
3. **The backend architecture is appropriate for the team size.** A modular monolith is a better starting point than microservices for this project.
4. **The provider adapter idea is strong.** The crop engine should consume normalized environmental features rather than calling NASA services directly.
5. **The scientific caveats are mostly responsible.** The documents correctly warn that POWER is not a forecast, satellite data cannot prove a farmer action, missing observations must not be punished, and soil nutrients require local measurements or clearly labelled estimates.
6. **The API contract is more than a list of routes.** It contains useful sample requests and responses, asynchronous scan status, ownership notes, and a common error format.
7. **The master handoff is a useful source of truth.** It contains deeper material that the short planning files do not repeat. Keep it as the main specification.

---

## 3. Critical corrections required before Phase 1

### C1 — Correct the false “risk register created” completion claim

**Files:** `PROJECT_STATUS.md`, `DEVELOPMENT_PLAN.md`

The Phase 0 acceptance criteria say a risk register was created, and `PROJECT_STATUS.md` marks Phase 0 complete. But the submitted ZIP contains no `RISK_REGISTER.md`, and the development plan does not include a risk register with likelihood, impact, mitigation, owner, and trigger.

**Required fix:** Create `docs/RISK_REGISTER.md` with at least these risks:

- NASA service outage, latency, authentication, or rate limiting.
- Product/parameter not available for chosen coordinates or dates.
- Spatial support too coarse for a small farm.
- NASA/soil/crop data use incompatible temporal or spatial units.
- Missing or poor-quality satellite observations.
- No verified regional crop calendar or agronomic rules.
- Soil test unavailable or incomplete.
- Recommendation outputs appear more certain than the evidence supports.
- PostGIS/Redis setup friction on team members' machines.
- API contract drift between backend and frontend.
- Agent-generated code changes or migrations break working modules.
- Hackathon time overrun and scope creep.

For each risk include: probability, impact, mitigation, owner, fallback, and the phase where it must be resolved.

Update `PROJECT_STATUS.md` so it says the risk register is complete only after the file exists and has been reviewed.

### C2 — Make the recommendation API return all three required strategies

**File:** `API_CONTRACTS.md`, Recommendations section.

The challenge requires at least three rotation strategies, including the farmer's current rotation. The current sample response contains only:

- `BASELINE`
- `WATER_EFFICIENT`

It is missing the required `SOIL_REGENERATION` option (the “Nitrogen Battery” display card). The sample should include all three options and show multi-season sequences, not only a single crop row per option.

**Required fix:** Add a third `SOIL_REGENERATION` object. Define the stable enum values for all strategy types. Use a multi-season sequence over a clearly specified planning horizon. Make the baseline exactly reflect farmer-entered crop history/current practice; do not invent a baseline.

Also mark all example scores and benefits as illustrative fixtures, not verified results. Remove unsupported example claims such as “15–25% lower seasonal water demand” unless the calculation method, crop coefficients, baseline, units, and evidence source are explicitly supplied. A sample payload must not look like a measured or validated promise.

### C3 — Correct NASA POWER data classification and provenance

**Files:** `DATA_PROVENANCE.md`, `API_CONTRACTS.md`, and the master handoff where applicable.

The current data-category table describes `OBSERVED` as a direct satellite/sensor measurement or retrieval, then gives NASA POWER temperature as an example. That is too broad and scientifically misleading.

NASA's own documentation states that POWER meteorological parameters originate from MERRA-2 and GEOS-IT assimilation/reanalysis products, while its solar data are inferred from satellite observations using radiative-transfer methods. The parameter source therefore matters. See:

- NASA POWER, [Meteorological Data Sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/)
- NASA POWER, [Data Sources FAQ](https://power.larc.nasa.gov/docs/faqs/data/)
- NASA POWER, [Methodology](https://power.larc.nasa.gov/docs/methodology/)

**Required fix:** Replace the overly simple category taxonomy with source-aware categories, for example:

- `REMOTE_SENSING_RETRIEVAL` — product-specific satellite retrieval, such as a soil-moisture or land-surface-temperature product.
- `REANALYSIS_OR_ASSIMILATION_ESTIMATE` — meteorological assimilation/reanalysis products such as MERRA-2/GEOS-IT.
- `MODELLED_ESTIMATE` — model-derived spatial products such as SoilGrids predictions or SMAP L4 model-assimilation products.
- `GROUND_MEASURED` — weather station or laboratory measurement.
- `USER_PROVIDED` — farmer-entered data.
- `DERIVED` — a calculation from traceable source values.
- `SCENARIO` — hypothetical simulation output.

Use the category that matches the specific parameter/product. Do not label all NASA POWER meteorological data as direct satellite observations. Update the example environmental API response accordingly.

### C4 — Fix NASA POWER resolution and time-standard statements

**File:** `DATA_PROVENANCE.md`; also update the example in `API_CONTRACTS.md`.

The registry says a common POWER grid is 0.5° × 0.5°, and the API example hardcodes `spatial_support: "0.5° grid cell"`. POWER documentation says data are provided at their original source spatial resolution; meteorological MERRA-2 fields are described at 0.5° latitude × 0.625° longitude. Different POWER parameters/sources can have different native resolutions. Do not assign one generic resolution to every POWER field.

NASA's Daily API also defaults to Local Solar Time (LST); UTC must be explicitly requested using `time-standard=UTC` when that is the chosen convention.

Sources:

- [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [NASA POWER Meteorological Sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/)
- [NASA POWER Data FAQ](https://power.larc.nasa.gov/docs/faqs/data/)

**Required fix:** Store spatial support and temporal convention per source/product/parameter. Update the sample response to use parameter-specific provenance and state that the API request must include `time-standard=UTC`. Avoid the fixed `0.5° grid cell` example unless it is verified for that exact parameter/product.

### C5 — Resolve the region-model/API mismatch

**Files:** `ARCHITECTURE_DECISIONS.md`, `API_CONTRACTS.md`, `DEVELOPMENT_PLAN.md`.

ADR-008 says the `geography` app/region model is deferred and the MVP will initially use `country_code`. But the API contract includes:

`GET /api/v1/regions/{region_id}/crop-calendar/`

No MVP region model is defined to supply that `region_id`.

**Required fix:** Choose one consistent MVP approach:

- Option A: Add a minimal `RegionAgronomyProfile` (or equivalent) in the `agronomy` app, with stable `region_code`, country, timezone, calendar and crop-catalog relationships; or
- Option B: Use a stable `region_code` slug in the API and define where the configuration is stored.

Do not leave an endpoint referencing a model that the architecture says will not exist.

### C6 — Align report export and the 80% review gate across scope documents

**Files:** `DEVELOPMENT_PLAN.md`, `API_CONTRACTS.md`, and master handoff if needed.

The master handoff lists report export in the prototype build table, while `DEVELOPMENT_PLAN.md` places PDF/CSV export in P1. The original product specification also describes a final verification gate with an 80% locked/provisional mechanic and expert-review instructions, but the Phase 8 plan does not explicitly define the completeness calculation or the `NEEDS_EXPERT_REVIEW` state.

**Required fix:** Make an explicit decision for each item:

- Report export: either include a minimal printable/downloadable summary in P0, or clearly move it to P1 in both documents.
- 80% gate: if retained, define it as a product-level **plan/input completeness** score, never scientific accuracy or NASA certification. Define how it is calculated, what missing fields cause the lock, and what reviewer action unlocks it. Add the data field, API response and acceptance criteria. If it is not needed for the demo, move it to P1 consistently.

### C7 — Mark incomplete API contracts as planned, or fill the missing contracts

**File:** `API_CONTRACTS.md`.

The document is named API Contracts, but several endpoints are only titles without request/response schemas or validation details. Important examples include zones, farmer context updates, environmental history, data-source status, crop catalog filters, report export, and reward/leaderboard behavior.

**Required fix:** It is not necessary to fully spec every future endpoint now. For each one, mark it as `P0`, `P1`, or `P2` and either provide the essential request/response contract or explicitly say “contract deferred; not part of MVP.” At minimum, define P0 contracts for:

- Registration and login identity field (choose username or email and make it consistent).
- Create/list/retrieve farm and create/list zones.
- Farmer context including current rotation, soil-test metadata, irrigation/water access, priorities and constraints.
- Start scan and retrieve job status.
- Retrieve environmental summary with source-aware data category and quality/freshness.
- Generate recommendations with exactly three strategies.
- Retrieve full strategy explanation and evidence.
- Create/retrieve simulation.
- Commit strategy and submit a self-reported check-in.

Define structured evidence objects. A plain text list such as `"NASA POWER climate summary"` is not enough for traceability. An evidence object should identify dataset/product, parameter, date range, spatial support, source record/snapshot, processing method/version, quality status, and explanatory relevance.

### C8 — Make the geography storage decision more precise

**File:** `ARCHITECTURE_DECISIONS.md`, ADR-003.

The decision currently prescribes `MultiPolygonField(geography=True, srid=4326)` for everything. PostGIS geography is convenient for geodesic measurements, but supports fewer functions and can be slower than geometry. This matters if the application later performs overlay, intersection, clipping, raster/vector operations, and zonal statistics.

PostGIS documents this trade-off here: [Geometry or Geography](https://postgis.net/documentation/faq/geometry-or-geography/).

**Required fix:** Record an explicit choice. A reasonable option is to store farm boundaries as SRID 4326 geometry and cast to geography for accurate area/distance calculations, or to use geography for storage only if the required operation set is confirmed. State how geometry operations will be performed and how area is calculated. Do not imply geography is automatically best for all GIS processing.

---

## 4. Important improvements (not all are blockers for Phase 1)

### I1 — Expand the data provenance registry

The main handoff discusses Landsat, MODIS, GRACE/GRACE-FO, SRTM and GEDI, but the standalone `DATA_PROVENANCE.md` only details POWER, GPM, SMAP, ECOSTRESS, SoilGrids, crops and market prices.

Add brief entries for the other datasets, even if they are explicitly marked `P2 / NOT INTEGRATED`. For each, record the intended use, official product/documentation link, native support/resolution caveat, key limitations, and why it is deferred. Do not claim integration just because it appears in the reference list.

### I2 — Clarify GPM priority

`DATA_PROVENANCE.md` calls GPM an MVP candidate, while `DEVELOPMENT_PLAN.md` calls it a Phase 3 stretch goal/P1. Choose one priority consistently. For a hackathon, it is reasonable to make POWER the first working source and GPM the next optional source, but the product should still make an honest case that the chosen data actually supports the challenge's Earth-observation objective.

### I3 — Make the local crop-data dependency explicit

The crop catalog is marked “not yet created.” That is acceptable in Phase 0, but the plan should identify who will source it, what minimum crops and seasons are required, what sources are acceptable, and how unreviewed demo rules will be labeled. Do not let an LLM invent crop calendars or water coefficients.

### I4 — Clarify the simulation timeline

The four UI nodes (Present, +6 months, +1 year, +2 years) should be display checkpoints mapped onto the selected region's actual crop seasons. A fixed six-month step is not necessarily a valid growing season. The API should preserve the season/calendar dates used by each simulation step.

### I5 — Provide environment reproducibility

Phase 1 should consider a `docker-compose.yml` for PostgreSQL/PostGIS and Redis, with Django and Vite optionally run locally. This reduces machine-specific setup friction. If Docker is not used, document exact supported local installation versions. Pin compatible dependency versions and include Windows setup instructions because the team is developing on Windows.

### I6 — Define data completeness and confidence separately

The API uses `data_completeness: 0.65` and `confidence: "medium"`, but their calculation methods are not defined in the API contracts. Define them separately:

- `data_completeness`: required input/data coverage present divided by total required inputs/data checks, with an explicit denominator and weighting policy.
- `confidence`: evidence quality/suitability for a particular claim or recommendation; it should not be derived by simply copying data completeness.

If no defensible method exists yet, return a structured explanation such as `NOT_ASSESSED` rather than inventing a numeric score.

### I7 — Align app structure with actual MVP scope

The architecture proposes 11 Django apps, but Phase 1 asks for empty app scaffolding while the plan defers some apps. Keep Phase 1 minimal. Create only the apps needed for the first vertical slice; document the future app boundaries instead of generating many empty Django apps.

---

## 5. Recommended decisions to unblock the team

Unless the team strongly disagrees, use these as provisional decisions:

| Decision | Recommended choice | Can Phase 1 proceed without it? |
|---|---|---|
| Architecture | Modular Django monolith | Yes — already accepted |
| Local development | Docker Compose for PostGIS + Redis; Django/Vite local | No blocker if another reproducible setup is documented |
| Demo region | Provisionally Gharbia/Nile Delta, but keep region config data-driven | Yes |
| Farmer persona | Small-to-medium irrigated farm; confirm with team | Yes |
| Map stack | Leaflet + a compatible drawing plugin for MVP; keep GeoJSON API-neutral | Yes |
| Auth identity | Decide email or username before auth implementation in Phase 2 | Yes for Phase 1 |
| NASA MVP data | NASA POWER first; verify exact variables and use source-aware category; one EO product next if feasible | Yes |
| Report export | P1 unless the team can build a small printable summary after core journey works | Yes |
| 80% gate | P1 unless demo judging specifically needs it; if used, score plan completeness only | Yes |
| LLM explanation | Defer; deterministic engine is source of truth | Yes |

---

## 6. What Phase 0 should do next

Ask the current coding agent to apply only the documentation fixes in Section 3 and the high-value improvements in Section 4.

The agent must:

1. Read this review and all existing project docs.
2. Update `PROJECT_STATUS.md`, `DEVELOPMENT_PLAN.md`, `ARCHITECTURE_DECISIONS.md`, `API_CONTRACTS.md`, and `DATA_PROVENANCE.md` consistently.
3. Create `RISK_REGISTER.md` and include it in the repository audit.
4. Resolve the three-strategy API example and structured evidence schema.
5. Correct NASA POWER provenance, category, resolution, and UTC handling.
6. Resolve the region-model/API mismatch.
7. Align report export and 80% gate scope.
8. Clearly label sample values as illustrative.
9. Add a concise Phase 0 decision log and mark unresolved team decisions honestly.
10. Do not create or modify application code, install packages, or begin Phase 1.

Then produce a short correction summary and stop.

---

## 7. Revised Phase 0 acceptance checklist

Phase 0 can be marked complete only when all of the following are true:

- [ ] The master project requirements are summarized into a realistic P0 scope.
- [ ] The repository audit matches the actual workspace.
- [ ] The modular architecture and app boundaries are documented.
- [ ] Database model responsibilities and major relationships are documented (the ER diagram may live in the master handoff).
- [ ] P0 API contracts cover the end-to-end MVP and include all three rotation strategies.
- [ ] NASA data sources have correct product/source classifications, units, temporal and spatial support caveats, access methods, and limitations.
- [ ] NASA POWER meteorology is not mislabeled as direct satellite observation.
- [ ] Region/calendar routes match the planned models.
- [ ] The risk register exists and has owners/mitigations.
- [ ] P0/P1/P2 scope is consistent across all docs.
- [ ] The report export and 80% completeness gate decisions are consistent.
- [ ] Unresolved team decisions are explicitly listed with owners.
- [ ] Phase 1 acceptance criteria are testable and reproducible.
- [ ] No application implementation is started prematurely.

**Final state after corrections:** `PHASE 0 — APPROVED; READY FOR PHASE 1`.

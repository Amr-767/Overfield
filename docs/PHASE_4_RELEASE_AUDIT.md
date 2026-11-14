# Overfield — Phase 4 Release-Gate Audit

**Audit date:** 2026-11-14
**Scope:** Phase 4 — environmental indicators, NASA POWER pipeline, geospatial behaviour,
API/permissions, frontend, documentation and Phase 5 readiness.
**Tree audited:** `crop-intelligence-rotation-engine` (contains Phase 4 plus the already
present Phase 5 code; this audit did not author Phase 5 features).
**Runtime:** Dockerized Django 6 / Python 3.14 / PostGIS 17-3.5, Redis and Celery.
**Status:** **CONDITIONAL — ready to continue Phase 5 development; not approved for
production deployment.**

> Honesty note: the audit was interrupted by a publishing request while Phase 5 work was
> already uncommitted in the tree. This report therefore audits the combined tree and
> explicitly marks what was not run. Nothing below is inferred from a planning document.

---

## 1. Executive summary

Phase 4 is **functionally sound**: the NASA POWER provider, persistence, Celery tasks,
four environmental indicators, summary API, ownership rules and geospatial validation all
pass their automated suites, and the architectural honesty rules (null scores, missing ≠
zero, freshness ≠ confidence, soil provenance, market unavailability) are enforced in code
and covered by regression tests.

**Verdict: CONDITIONAL.**

- Critical business-logic and data-integrity requirements: **PASS** (tested).
- Browser-level end-to-end journey and live NASA network smoke: **NOT RUN** (no harness /
  deliberately offline test suite). These are release activities, not development blockers.
- Frontend environmental dashboard: **NOT IMPLEMENTED** — planned for Phase 7, not Phase 4.
- Production crop catalogue/calendar: **absent by design**; rotation correctly fails closed.
- Non-fatal quality issues: frontend bundle size (819.72 kB / 233.06 kB gzip), no explicit
  expired-token test, no load/performance measurement beyond a query-budget assertion.

Phase 5 was already started before this verdict was written. The evidence supports
continuing Phase 5 development. It does **not** support a production release claim.

---

## 2. Implementation inventory (Phase 4)

| Area | Actual implementation |
|---|---|
| Accounts/auth | `apps.accounts` — registration, `FarmerProfile`, `/me/`, SimpleJWT token obtain/refresh. |
| Farms | `apps.farms` — `Farm`, `FarmZone`, `FarmerContext`, `FarmCropHistory`; owner-scoped CRUD, boundary validation, geodesic area. |
| NASA provider | `apps.earth_data.providers.power` + `power_transport` — POWER daily API, parameter catalogue, sentinel handling, bounded retries. |
| Persistence | `apps.earth_data.services` — `DatasetSource`, `DataFetchJob`, `EnvironmentalObservation`; checksum/idempotent persistence, job lifecycle. |
| Background work | `apps.earth_data.tasks` + `apps.core.tasks` — Celery ingestion, retries, duplicate-scan protection, stale-job retirement. |
| Observations API | `apps.earth_data.views` — farm scans, job status, daily observations, owner scoping. |
| Indicators | `apps.indicators` — `contract`, `coverage`, `selectors`, `services/{water,heat,soil,market}`, `summary`. |
| Summary API | `GET /api/v1/farms/{id}/environment/current/` — on-demand computation, `window_days` validation, 6-query budget. |
| Frontend | React 19 + Vite: auth, onboarding, farms, farm detail, rotation explorer (Phase 5). **No environmental dashboard yet.** |
| Docs | `README`, `PROJECT_STATUS`, `DEVELOPMENT_PLAN`, `ARCHITECTURE_DECISIONS`, `API_CONTRACTS`, `DATA_PROVENANCE`, `ENVIRONMENTAL_INDICATORS`, `HACKATHON_DATA_SOURCE_MATRIX`, `RISK_REGISTER`, `GIT_WORKFLOW`. |

Only **NASA POWER** is integrated. GPM IMERG, SMAP, MODIS/VIIRS, ECOSTRESS, Landsat,
Sentinel-2, HLS, GAEZ, SRTM, GLDAS and ERA5 are evaluated but not integrated. U.S.-only
products (including NLCD, SSURGO, CDL, PRISM) are excluded for the Gharbia demo region.

---

## 3. Requirements traceability matrix

Legend: ✅ verified by automated test · ⚠️ partially verified / gap stated · ⛔ not implemented.

| # | Requirement | Implementation | Test evidence | Result |
|---|---|---|---|---|
| R1 | Never manufacture a score to fill a value | `IndicatorResult.score` is always `None`; serializers emit it | `test_indicator_summary_api.test_no_numeric_scores`; `test_indicator_contract` | ✅ |
| R2 | Missing data ≠ zero | `selectors.parameter_series` maps `MISSING` → `None`, absent days stay absent | `test_indicator_selectors.test_missing_quality_is_returned_as_none`; water/heat partial tests | ✅ |
| R3 | Freshness ≠ confidence | `coverage.py` bands + independent freshness helper; grid-cell confidence cap | `test_indicator_heat`, `test_indicator_water`, `test_indicator_summary_api` | ✅ |
| R4 | Soil lab vs farmer-reported provenance distinct | `SoilProfile.source`, `soil_source`; provenance on every measurement | `test_indicator_soil`, `test_indicator_selectors` | ✅ |
| R5 | No NPK deficiency/sufficiency claims | Soil service reports values + qualitative bands only; explicit limitation strings | `test_indicator_soil`; code inspection `services/soil.py` | ✅ |
| R6 | No water-holding capacity from texture | Texture emitted as qualitative context only | `test_indicator_soil`; `services/soil.py` limitation text | ✅ |
| R7 | Never substitute today for a missing soil sample date | `sample_freshness(None)` → `UNKNOWN`; period/as_of `None` | `test_indicator_summary_api.test_soil_without_sample_date_has_no_synthetic_period` | ✅ |
| R8 | Market `UNAVAILABLE`, null score/period | `services/market.py` | `test_indicator_market`; `test_market_unavailable_with_null_score_and_period` | ✅ |
| R9 | No NASA estimate presented as field measurement | Source metadata + `GRID_CELL_CONFIDENCE_CAP` + wording in responses | `test_indicator_selectors.test_source_reference_matches_the_catalogue`; heat confidence cap test | ✅ |
| R10 | Every result traceable to source + method | `SourceReference`, `Methodology`, evidence IDs | `test_indicator_contract`; summary API shape tests | ✅ |
| R11 | Farm ownership enforced | Owner-filtered querysets; cross-user → 404 | `test_farm_permissions` (8), `test_earth_data_api`, summary/rotation API tests | ✅ |
| R12 | Summary must not mix farms | Per-farm querysets + farm-scoped selector tests | `test_indicator_selectors.test_series_is_farm_scoped`; summary API owner tests | ✅ |
| R13 | `MISSING` rows must not advance the window | `latest_observation_date` filters usable quality | `test_latest_observation_date_ignores_missing_quality_rows`; Phase 4F regression | ✅ |
| R14 | Top-level freshness aggregation documented and correct | `summary.py` freshness from newest usable catalogue observation | `test_top_level_freshness_follows_usable_catalogue_observations` | ✅ |
| R15 | Heat coverage not overestimated across incompatible dates | Headline coverage = weakest required parameter | `test_coverage_is_not_overestimated_when_parameters_use_different_dates` | ✅ |
| R16 | Provider robustness (sentinels, malformed, timeouts, 429/503) | `power.py`, `power_transport.py` | `test_power_client` (30 tests) | ✅ |
| R17 | Failed fetch must not corrupt valid data | Transactional persistence; failure recorded on job | `test_earth_data_tasks.test_failed_request_does_not_corrupt_existing_observations` | ✅ |
| R18 | Idempotent/duplicate-safe ingestion | Checksum + unique active job + update-on-reimport | `test_earth_data_persistence`, `test_earth_data_tasks` | ✅ |
| R19 | Migration consistency from a fresh DB | Additive migrations; test DB built each run | `makemigrations --check --dry-run` → no changes; suite creates test DB | ✅ |
| R20 | Geometry validation (closure, self-intersection, SRID, order, area) | `domain_services/geometry` | `test_geometry_services` (18) | ✅ |
| R21 | UI must not show null as zero or hide missing data | Rotation page displays missing/limitations; indicators UI absent | Frontend unit tests (61) | ⚠️ indicators UI not implemented |
| R22 | Browser end-to-end journeys | No Playwright/Cypress harness | — | ⛔ NOT RUN |
| R23 | Live NASA network smoke | Standard suite is offline by design | mocked transport only | ⛔ NOT RUN |
| R24 | Crop rotation data requirements documented and fail-closed | Phase 5 engine + `PHASE_5_STATUS.md` | `test_rotation_engine` (8), `test_rotation_api` (6), `test_agronomy` (16) | ✅ |

---

## 4. Backend results

Command (Docker/PostGIS runtime):

```
docker compose --env-file .env -f infra/compose.yaml exec -T backend python manage.py test tests
```

**Result: Ran 325 tests — OK (0 failures, 0 errors).**

| Suite | Tests |
|---|---|
| `test_accounts_api` | 9 |
| `test_agronomy` | 16 |
| `test_celery` | 7 |
| `test_earth_data_api` | 32 |
| `test_earth_data_persistence` | 19 |
| `test_earth_data_tasks` | 18 |
| `test_farmer_context` | 12 |
| `test_farms_api` | 16 |
| `test_farm_permissions` | 8 |
| `test_geometry_services` | 18 |
| `test_health` | 3 |
| `test_indicator_contract` | 16 |
| `test_indicator_heat` | 16 |
| `test_indicator_market` | 8 |
| `test_indicator_selectors` | 15 |
| `test_indicator_soil` | 19 |
| `test_indicator_summary_api` | 32 |
| `test_indicator_water` | 14 |
| `test_power_client` | 30 |
| `test_rotation_api` | 6 |
| `test_rotation_engine` | 8 |
| `test_settings` | 3 |

Other backend checks:

| Check | Result |
|---|---|
| `python manage.py check` | No issues (exit 0) |
| `python manage.py makemigrations --check --dry-run` | No changes detected (exit 0) |
| Fresh test DB creation + migrations | Succeeds on every suite run |
| `git diff --check` | Clean |

### Phase 4F regression cases (explicitly re-tested)

1. `MISSING` observations do not advance the window — ✅ tested at selector and API level.
2. Top-level freshness reflects usable catalogue observations — ✅ tested.
3. Soil without a sample date has no synthetic period — ✅ tested (period and `as_of` null).
4. Heat coverage uses the weakest parameter across incompatible dates — ✅ tested.
5. Market keeps `UNAVAILABLE`, `score = null`, `period = null` — ✅ tested twice (service + API).
6. One missing indicator does not invalidate unrelated indicators — ✅ tested (water missing,
   heat/soil OK, `data_status = PARTIAL`).

### Gaps

- No explicit test for **expired** JWT tokens (anonymous and cross-user are tested; expiry
  relies on SimpleJWT defaults). Marked **NOT VERIFIED**, low risk.
- No load/latency benchmark. The only performance assertion is the summary query budget
  (`assertNumQueries(6)`), which passes.

---

## 5. Frontend results

| Command | Result |
|---|---|
| `npm test -- --run` | **61 passed** across 8 files |
| `npm run lint` (`oxlint`) | exit 0, no findings |
| `npm run build` (`tsc -b && vite build`) | exit 0 |

Measured bundle output:

| Asset | Size | Gzip |
|---|---|---|
| `dist/assets/index-*.js` | **819.72 kB** | 233.06 kB |
| `dist/assets/index-*.css` | 67.79 kB | 18.49 kB |

The >500 kB chunk warning is real and should be addressed with code-splitting before a
public demo, but it is not a correctness defect.

### Scope finding

The Phase 4 **environmental dashboard does not exist**. Phase 7 in `DEVELOPMENT_PLAN.md`
owns the farmer-facing dashboard. The implemented UI covers auth, onboarding, farms,
farm detail and the Phase 5 rotation explorer. Therefore the audit's Stage 6 dashboard
checks (loading/empty/partial/stale indicator states, unit display, source attribution in
the UI) are **NOT APPLICABLE to Phase 4** and remain a Phase 7 deliverable.

Frontend tests mock HTTP; they do not prove live backend integration. No live browser E2E
was run.

---

## 6. NASA data pipeline results

| Check | Evidence | Result |
|---|---|---|
| Request construction, parameter names/units, dates, coordinates | `test_power_client` (30) | ✅ |
| Sentinel `-999` and null → missing, never zero | `test_missing_values_become_none_not_sentinel` | ✅ |
| Malformed JSON / unexpected structure | provider response-error tests | ✅ |
| Invalid dates/coords rejected before request | provider validation tests | ✅ |
| Timeouts, connection failures, bounded retries | retry tests (success after retry, exhaustion) | ✅ |
| HTTP 429/503 and `Retry-After` (seconds, HTTP date, capped) | retry tests | ✅ |
| Duplicate/concurrent scans rejected | task tests | ✅ |
| Stale running job retired and replaced | task tests | ✅ |
| Partial days / missing days recorded honestly | persistence + task tests | ✅ |
| Failure does not corrupt prior observations | task test | ✅ |
| Every stored observation has farm, source, parameter, unit, date, quality | model constraints + persistence tests | ✅ |
| Live NASA availability | not called by the suite | ⛔ NOT RUN |

---

## 7. Environmental indicator results

### WATER — ✅
Rainfall totals over **covered days only**, rainy-day count (`≥ 1.0 mm`), max daily
rainfall, longest observed dry run with a limitation when the window is incomplete. No
irrigation, soil-moisture, ET or water-stress claim. 14 unit tests + selector/API coverage.

### HEAT — ✅
`T2M`, `T2M_MAX`, `T2M_MIN` from stored observations; hot/very-hot/cool-night exposure
counts. Coverage is the **weakest required parameter**, so mixed observation dates cannot
produce false completeness. Confidence is capped at MEDIUM because MERRA-2 is a grid-cell
estimate. 16 unit tests, including the disjoint-date regression.

### SOIL — ✅
Farmer/lab provenance preserved, qualitative pH band, organic carbon, N/P/K values,
texture as context. No deficiency/sufficiency verdict, no water-holding capacity, no
synthetic sample date. Sample age and freshness are reported separately. 19 unit tests.

### MARKET — ✅
Always `UNAVAILABLE`, `score = null`, `period = null`, no measurements, explicit missing
input. 8 unit tests plus API regression.

### Cross-indicator — ✅
Partial availability, mixed freshness, zero vs missing, and one-failed-indicator isolation
are covered by the 32 summary API tests. No score is produced at any level.

---

## 8. Geospatial results

| Check | Evidence | Result |
|---|---|---|
| Polygon normalisation to MultiPolygon, SRID 4326 | `test_geometry_services` | ✅ |
| Unclosed ring, self-intersection, zero area, too few positions | geometry tests | ✅ |
| Longitude/latitude range and order | geometry tests | ✅ |
| Geodesic area (metres/hectares, not degrees) | geometry + PostGIS geography test | ✅ |
| One-degree box near equator ≈ 12,300 ha | geometry test | ✅ |
| Implausibly large farm rejected | geometry test | ✅ |
| Farm boundary vs point fallback; largest-part point-on-surface | task tests | ✅ |
| Spatial filtering / owner scoping | farms API + permission tests | ✅ |
| NASA resolution honesty | grid-cell confidence cap; wording in docs | ✅ |

No test claims a 0.5° × 0.625° NASA cell is a field measurement, and no 30 m satellite
product is integrated.

---

## 9. Crop rotation and dataset audit

- **Engine exists:** yes (Phase 5.3), deterministic evidence-readiness only.
- **Consumes:** farm crop history, farmer context, approved regional calendar, eligible
  reviewer-approved crop traits, recent stored NASA POWER evidence.
- **Produces:** candidates only when calendar + profiles + evidence are present; otherwise
  `INSUFFICIENT_EVIDENCE` with named missing inputs. No score, rank, yield or profit claim.
- **Production data:** none. No agricultural dataset is approved for import, so no crop
  trait or Gharbia calendar is seeded. This is correct fail-closed behaviour, now asserted
  by a test that requires `regional_crop_calendar`, `eligible_crop_profiles` and
  `crop_history` in the response and an explicit "No rotation is recommended" limitation.
- **Review gate (fixed during this audit):** candidate/list eligibility now requires
  `approval_status = APPROVED` **and** `approved_geographic_applicability`; a source's own
  `VALID`/`GENERAL` claim alone is no longer region-ready. Four regression tests cover
  pending, staff-only approval, approved and rejected states.
- **NLCD:** U.S.-only; **not** applicable to Gharbia and not used. No overlay is emitted.
- **MODIS MCD12Q1:** not integrated, not approved; 500 m pixels must never be presented as
  farm-level detail.
- **Unsupported claims that must not be made:** crop suitability, winter/summer crop
  assignment for Gharbia, yield/profit outcomes, soil-carbon benefits, pest/disease risk —
  all require approved sources and reviewed rules that do not exist.

**Phase 5 readiness:** the engine's *mechanics* are ready; its *knowledge base* is empty by
design. This is documented, tested and surfaced to the API consumer.

---

## 10. Defects and fixes

| # | Severity | Defect | Fix | Regression |
|---|---|---|---|---|
| D1 | Major | Stale soil test asserted a synthetic current-date period | Test aligned to nullable-period contract | `test_soil_without_sample_date_has_no_synthetic_period` and related |
| D2 | Major | `MISSING` rows could advance the summary window | `latest_observation_date` excludes unusable rows | selector + API regressions |
| D3 | Major | Heat coverage could be overestimated across dates | Weakest-parameter coverage enforced and tested | disjoint-date regression |
| D4 | Major | Market period inherited the climate window | `period=None` enforced | service + API regressions |
| D5 | Critical (Phase 5) | `agronomy` app failed to import (`NameError`) | Enum moved before use | full suite import |
| D6 | Critical (Phase 5) | Migration drift (~40 operations) | Additive `0004_sync_phase5_models` | `makemigrations --check` clean |
| D7 | Major (Phase 5) | Explanation endpoint `KeyError` | reads `environmental_digest` | rotation API test |
| D8 | Major (Phase 5) | Source claims were treated as approved evidence | Import records claims; review gate now requires staff approval | 4 new gate tests |

All fixes are committed on the Phase 5 branch; no historical migration was edited and no
remote history was rewritten.

---

## 11. Remaining risks

### Critical blockers (none for Phase 5 development)
- None identified in Phase 4 logic. Production deployment is blocked by the unverified
  items below, not by a known correctness defect.

### Important issues
1. **No browser E2E** against a live backend — journeys are covered by API/integration
   tests, not a real browser session.
2. **No live NASA smoke test** — provider correctness is mocked; first real scan must be
   validated manually in a staging environment.
3. **No production crop catalogue/calendar** — rotation is intentionally unavailable.
4. **Frontend bundle 819.72 kB** — needs code-splitting before a public demo.
5. **Expired-token behaviour untested** — relies on SimpleJWT defaults.
6. **Phase 4 dashboard absent** — Phase 7 scope, but the release gate cannot claim a
   complete farmer-facing Phase 4 experience.

### Optional improvements
- Add a cached summary or explicit caching decision (currently on-demand, 6 queries).
- Add per-indicator API contract tests for empty/zero-valued series beyond the current mix.
- Add a CI workflow that runs backend + frontend + migration checks on every push.

---

## 12. Phase 5 readiness checklist

- [x] Phase 4F stale test corrected
- [x] README / PROJECT_STATUS / DEVELOPMENT_PLAN agree with the repository
- [x] Backend suite green (325 tests)
- [x] Frontend suite green (61 tests), lint and build clean
- [x] Migrations consistent from a fresh database
- [x] NASA provider behaviour and provenance tested offline
- [x] Indicator contracts validated (WATER/HEAT/SOIL/MARKET)
- [x] Missing/null/freshness/confidence semantics enforced
- [x] Geospatial validation and ownership verified
- [x] Backend API journeys covered by integration tests
- [x] Crop-rotation data requirements and limitations documented
- [x] No unapproved dataset or fabricated crop trait
- [x] No known critical correctness/security defect
- [ ] Browser E2E run against a live stack (release activity)
- [ ] Live NASA scan validated in staging (release activity)
- [ ] Bundle size addressed before public demo (release activity)

---

## 13. Final recommendation

**Can we safely start Phase 5 now? YES** — and in practice it has already started.

The Phase 4 logic, data-integrity rules, provider pipeline, indicators, geospatial
validation and ownership model are verified by 325 passing backend tests and 61 passing
frontend tests, with no known critical defect. The remaining items are verification and
release-environment activities (live browser E2E, live NASA smoke, bundle optimisation),
not development blockers.

**Can we call Phase 4 production-ready? NO.** Treat this as **CONDITIONAL**: complete the
three unchecked release activities in §12, add the missing expired-token test, and keep the
rotation catalogue empty until an approved Gharbia dataset and reviewer exist.

No Phase 6 feature code was added during this audit.

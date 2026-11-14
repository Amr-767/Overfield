# Overfield — Phase 7 Setup and Slice Plan

**Date:** 2026-11-14
**Branch:** `phase/7-farmer-experience` (created from the published Phase 6 tip `7c675b8`)
**Status:** Setup only. No Phase 7 feature code exists yet.

This document fixes the scope, order of work and acceptance gates for Phase 7 —
**Farmer-Facing React Experience and Dashboard** — before implementation begins.

---

## 1. Goal

Turn the already-implemented backend capabilities into **one coherent farmer journey inside
the SPA**: see the farm, fetch NASA POWER evidence, read the environmental summary honestly,
and move into rotation assessment and scenario simulation without manual database editing.

Phase 7 is primarily a frontend integration phase. The backend endpoints already exist and
are tested; this phase must consume them, not duplicate their logic.

## 2. Verified current state

### Backend capabilities available to the UI

| Capability | Endpoint | State |
|---|---|---|
| Trigger a NASA POWER scan | `POST /api/v1/farms/{id}/scans/` | Implemented, returns `202` + job |
| Poll a scan job | `GET /api/v1/data-jobs/{job_id}/` | Implemented |
| Daily stored observations | `GET /api/v1/farms/{id}/environment/daily/` | Implemented, paginated |
| Four-indicator summary | `GET /api/v1/farms/{id}/environment/current/` | Implemented |
| Rotation assessment | `POST /api/v1/farms/{id}/recommendations/` | Implemented, currently `INSUFFICIENT_EVIDENCE` |
| Scenario simulation | `/api/v1/farms/{id}/simulations/`, `/api/v1/simulations/{id}/` | Implemented (Phase 6) |

### Frontend surfaces already implemented

- Authentication (register, login, session refresh) and protected routes.
- Five-step onboarding wizard with map drawing and backend-validated area.
- Farm list and farm detail (farm data, farmer context, zones read-only).
- Crop rotation explorer.
- Scenario lab (`/simulations`).

### Confirmed gaps

1. **No environmental API client.** `frontend/src/api/` has no earth-data module.
2. **No scan trigger or job polling UI.** The farmer cannot request fresh NASA POWER data
   from the SPA.
3. **No environmental dashboard.** The four indicators, their units, periods, freshness,
   missing inputs and source references are not displayed anywhere.
4. **No farm-level overview.** The home page is static; it does not summarise the selected
   farm or link the rotation/simulation outcomes.
5. **No indicator gauge components.** The planned “elemental gauges” do not exist. They must
   be labelled composite indicators, never invented 0–100 scores.
6. **No responsive/accessibility pass** across the new journey.

## 3. Non-negotiable constraints

1. **No fabricated values or scores.** `score` stays `null`; no 0–100 gauge, rank or
   “suitability” claim may be introduced.
2. **Missing stays missing.** A missing observation or indicator renders as unknown, never
   as zero, and never as a green status.
3. **Freshness is not confidence.** Show the backend `freshness` label separately from any
   coverage/confidence information.
4. **Source, unit, period and spatial support are visible** wherever an environmental value
   is shown. NASA POWER is a grid-cell reanalysis estimate, not a field measurement.
5. **No crop claims while the catalogue is empty.** Rotation remains `INSUFFICIENT_EVIDENCE`
   and the UI must say so explicitly; scenario simulation stays environment-only.
6. **No new data sources, ML or architecture redesign.** No NLCD/MODIS for Gharbia.
7. **Existing contracts stay intact.** Do not change Phase 4–6 API shapes to fit the UI; add
   display-only fields only if unavoidable and tested.
8. **Owner scoping is preserved.** Another farmer's farm is `404`; expired session is `401`.
9. **No secrets or credentials in the frontend bundle.**

## 4. Proposed slices

### 7.1 Environmental data client and scan flow

- Add `src/api/environment.ts` with typed wrappers for the scan, job status, daily series and
  current-summary endpoints (reuse `apiRequest` and the existing JWT handling).
- Add a scan control on the farm page: idle → queued/running → succeeded / partially succeeded
  / failed, with bounded polling and a clear stop condition.
- Surface duplicate-scan and provider-failure responses without inventing success.

**Exit:** a farmer can trigger a scan and see the real job outcome; component tests cover
loading, success, partial and failure.

### 7.2 Farm environmental dashboard

- Indicator cards for WATER, HEAT, SOIL and MARKET driven entirely by the summary endpoint.
- Each card shows: status, summary text, measurements with unit, source/product, period,
  freshness, coverage and the backend `missing` list.
- MARKET remains `UNAVAILABLE`; SOIL keeps farmer-reported/lab provenance; no deficiency,
  yield or suitability claim.
- If visual gauges are used, they are labelled **composite indicators** with an explicit
  unknown state and no fabricated numeric score.

**Exit:** dashboard contract tests cover OK, partial, stale, insufficient and unavailable
states; no zero-filled or scored values.

### 7.3 Farm overview and journey links

- Add a compact farm overview (latest summary, freshness, last scan) to the farm detail or
  home area.
- Link the journey: farm → scan → environmental summary → rotation explorer → scenario lab,
  carrying the selected farm.
- Keep empty-farm and no-observation states actionable.

**Exit:** the full journey is reachable by clicks only; no manual URL or DB editing.

### 7.4 State and error hardening

- Loading, empty, partial, stale, failed and unauthorized states for every new surface.
- Explicit handling for `401` (session expired), `404` (not owned / not found) and provider
  `429/503` surfaced by the scan job.
- Verify that a failed scan or missing indicator never invalidates unrelated indicators.

**Exit:** component/integration tests cover each state; no silent fallback to demo data.

### 7.5 Responsive, accessibility and bundle

- Mobile layout for the dashboard and scan flow; keyboard-operable controls; labelled
  regions and `aria-live` for async status.
- Reuse existing CSS tokens and components (`page`, `rotation-panel`, `rotation-tag`,
  `Banner`, `Field`).
- Re-measure the production bundle; apply route-level code-splitting only if it materially
  reduces the >500 kB warning.

**Exit:** lint/build clean, responsive checks documented, no accessibility regressions.

### 7.6 Verification gate

- Full backend suite, `manage.py check`, `makemigrations --check --dry-run`.
- Full frontend suite, lint and production build.
- Documented evidence in `docs/PHASE_7_STATUS.md`.

## 5. Acceptance criteria (Phase 7 overall)

- A farmer can go from an owned farm to a fetched environmental summary, then to rotation and
  scenario simulation, using only the UI.
- No manual database editing, no mocked production data and no invented values.
- Loading, empty, partial, stale and failed states are handled and visually distinct.
- No API/UI string presents NASA POWER as crop biology or a field measurement.
- No 0–100 score, ranking, yield or profit estimate is introduced.
- Mobile responsive and keyboard accessible.
- Backend and frontend suites, lint and build are green.

## 6. Dependencies and blockers

| Dependency | State |
|---|---|
| Phase 6 environment-only simulation | Published on `overfield/phase/6-simulation` (`7c675b8`) |
| Phase 4 summary endpoint and scan APIs | Implemented and tested |
| Live NASA POWER reachability | Required for a real scan; the automated suite is offline |
| Approved Gharbia crop catalogue + calendar | **Missing** — rotation stays `INSUFFICIENT_EVIDENCE`; crop-level UI claims stay out of scope |

The dashboard may show the honest `INSUFFICIENT_EVIDENCE` / `UNAVAILABLE` states. It must not
hide them behind demo data.

## 7. Explicit non-goals

- New external datasets or providers.
- Crop traits, cultivar data, yield/profit or soil-carbon modelling.
- Machine learning or a new suitability score.
- Strategy commitment, check-ins, gamification and rewards (Phase 8).
- Rewriting Phase 4–6 contracts or historical migrations.

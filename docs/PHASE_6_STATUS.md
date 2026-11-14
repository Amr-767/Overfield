# Overfield — Phase 6 Status: Environment-Only Scenario Simulation

**Date:** 2026-11-14
**Branch:** `phase/6-simulation` (published to the `overfield` remote)
**Engine version:** `phase6-env-1.0.0`
**Verdict:** **DEMO READY** for the selected environment-only slice.
Crop-level scenario comparison is **BLOCKED** by the missing approved Gharbia catalogue and
calendar, and is refused rather than fabricated.

---

## 1. Objective (from the repository, not invented)

`docs/DEVELOPMENT_PLAN.md` Phase 6 — *Scenario Simulation and Strategy Comparison* — and
`docs/PHASE_6_SLICE_PLAN.md` define the goal: let a farmer explore explicitly hypothetical
season scenarios and compare strategies using existing evidence, without ever presenting an
assumption as an observation or a forecast.

Non-negotiable rules from the slice plan: no fabricated inputs, no forecast claim, no 0–100
scores, missing stays missing, reproducible SHA-256, approved sources only, owner scoping, no
destructive change.

## 2. Selected slice and justification

**Delivered:** environment-only scenario simulation over stored NASA POWER observations.

**Why not crop-level comparison:** the production agricultural catalogue is empty and no
Gharbia season calendar has been approved. A crop-level scenario would require inventing crop
traits, season dates or suitability thresholds, which the Phase 6 rules forbid. The slice plan
explicitly permits environment-only summaries until a calendar exists (§5). Requests that ask
for crop-level or strategy outcomes are therefore rejected with a clear `400`.

## 3. Implemented functionality

- `apps/simulations` Django app with additive models:
  - `SimulationRun` — farm, requester, mode, bounded adjustments, window, baseline dates,
    engine version, status, canonical input snapshot, SHA-256, stored result snapshot.
  - `SimulationStep` — four checkpoints (`PRESENT`, `+6 months`, `+1 year`, `+2 years`) with
    metrics, missing inputs, applied adjustments, assumptions and limitations.
- Pure deterministic engine (`apps/simulations/service.py`):
  - Modes `BASELINE`, `HOT_SCENARIO` (+2.00 °C), `DRY_SCENARIO` (rainfall × 0.70), `CUSTOM`.
  - Bounds: temperature delta −5.00…+5.00 °C; rainfall multiplier 0.20…2.00.
  - Environment metrics only: mean/max/min temperature, rainfall total, rainy days,
    hot days (max ≥ 35 °C), very hot days (max ≥ 40 °C), cool nights (min ≤ 5 °C),
    recorded-day counts. No crop, yield, profit or soil-carbon outcome.
  - Missing observations stay `null`; missing days are reported, never imputed.
  - Horizon checkpoints reuse the stored window and carry `as_of_date: null`, because no
    approved calendar exists to anchor a real future date.
  - Same inputs + engine version ⇒ identical payload and identical `input_sha256`.
- Owner-scoped API with persistence and validation.
- React "Scenario lab" page with farm/mode/window selection, custom bounds, recorded-vs-scenario
  differences, four checkpoint cards, missing evidence, limitations, source metadata and the
  reproducibility fingerprint.

## 4. API endpoints (implemented)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/farms/{farm_id}/simulations/` | create and store a scenario run |
| `GET` | `/api/v1/farms/{farm_id}/simulations/` | recent runs for one owned farm |
| `GET` | `/api/v1/simulations/{simulation_id}/` | stored run |
| `GET` | `/api/v1/simulations/{simulation_id}/steps/` | stored checkpoints |

Anonymous → `401`; another farmer's farm/run → `404`; invalid bounds/modes → `400`;
crop-level keys (`planning_seasons`, `crop_codes`, `strategy`, …) → `400` with the missing
catalogue/calendar explanation.

## 5. Database / migration changes

One additive migration: `apps/simulations/migrations/0001_initial.py`. No Phase 2–5 model,
route or historical migration was altered. `makemigrations --check --dry-run` reports no
changes.

## 6. Tests actually executed

| Check | Command | Result |
|---|---|---|
| Focused backend | `manage.py test tests.test_simulations` | **17 tests OK** |
| Full backend | `manage.py test tests` | **342 tests OK** (0 failures, 0 errors) |
| `manage.py check` | Docker/PostGIS runtime | No issues |
| `makemigrations --check --dry-run` | Docker/PostGIS runtime | No changes detected |
| Focused frontend | `vitest run src/pages/SimulationPage.test.tsx` | **5 tests passed** |
| Full frontend | `npm test -- --run` | **66 tests passed** (9 files) |
| Lint | `npm run lint` (oxlint) | exit 0 |
| Production build | `npm run build` | exit 0 |

Build output: `index-*.js` 836.69 kB (gzip 236.13 kB), `index-*.css` 70.55 kB (gzip 18.90 kB).
The >500 kB chunk warning remains a known, unrelated optimisation item.

Frontend tests mock HTTP; they do not prove live browser integration. No browser end-to-end
run or live NASA scan was performed in this session.

## 7. Phase 5 blocker verification

| ID | Finding | Effect on this slice |
|---|---|---|
| D1 | Crop-history gaps are non-blocking and reported as data gaps. | Not used: the simulation is environment-only. |
| D2 | `options = []` whenever the assessment is not ready. | Not used. |
| D3 | `trait_evaluation = NOT_EVALUATED`, `traits_evaluated: []`. | Not used; simulation never claims trait evaluation. |
| D4 | Region mismatch returns `201` + `region_code_mismatch` (no `500`). | Not used; tested by the existing rotation API suite. |

No Phase 5 workaround was required for this slice. The production rotation remains
`INSUFFICIENT_EVIDENCE` by design.

## 8. Known limitations

- **No crops.** Crop-level scenario outcomes are blocked until an approved Gharbia catalogue
  and calendar exist. The API refuses those requests.
- **No forecast.** All adjustments are `HYPOTHETICAL` / `USER_DECLARED_ASSUMPTION`.
- **No trajectory.** The horizon checkpoints reuse the stored window; they are not projections.
- **No scores.** `comparison.score` is `null`, `ranked` is `false`, no winner is declared.
- **Grid-cell data.** NASA POWER values are reanalysis estimates, not field measurements.
- **Staleness is visible, not corrected.** Freshness is reported from the newest stored
  observation; a stale farm keeps a stale baseline.
- **No browser E2E or live NASA smoke test** in this session; the frontend suite uses mocked
  transport.
- **Bundle size** remains above the 500 kB warning threshold.

## 9. Demo journey

1. Sign in and select an owned farm that has completed a NASA POWER scan.
2. Open **Scenario lab** in the navigation.
3. Choose `Hot scenario — +2 °C` and a stored window (for example 30 days).
4. Run the hypothetical scenario.
5. Read the hypothetical notice, baseline period and freshness.
6. Compare the recorded vs scenario metrics: hot-day counts and mean temperature change; note
   that rainfall is unchanged by a temperature-only scenario.
7. Select `Dry scenario — rainfall × 0.7` and run again: rainfall total falls while
   temperature is unchanged.
8. Open `Custom` to demonstrate the bounded inputs.
9. Inspect the four checkpoints: each states that the stored evidence is reused and that no
   future date is asserted.
10. Review missing inputs, limitations, NASA POWER source metadata and the input fingerprint.
11. If the farm has no stored observations, the run is stored as `INSUFFICIENT_EVIDENCE` with
    no invented value.

## 10. Classification

- **Selected slice (environment-only scenario simulation): DEMO READY.** End-to-end backend,
  persistence, API, frontend, loading/error/insufficient-evidence states and tests are in place
  and executed.
- **Crop-level strategy comparison: BLOCKED** by missing approved agricultural evidence; the
  product refuses it honestly rather than fabricating it.
- This does **not** make the whole platform complete.

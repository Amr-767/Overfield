# Overfield — Phase 6 Setup and Slice Plan

**Date:** 2026-11-14
**Branch:** `phase/6-simulation` (created from the Phase 5 tip)
**Status:** Setup only. No Phase 6 feature code, model, migration or route exists yet.

This document fixes the scope, order of work and acceptance gates for Phase 6 —
Scenario Simulation and Strategy Comparison — before any implementation begins.

---

## 1. Goal

Let a farmer explore **explicitly hypothetical** season scenarios and compare strategies,
using the evidence the project already has, without ever presenting an assumption as an
observation or a forecast.

Phase 6 answers "what changes if the scenario changes?" — not "what will happen?".

## 2. Non-negotiable constraints

1. **No fabricated inputs.** A scenario is a user-declared adjustment with documented
   bounds, not a NASA product. It must be labelled `HYPOTHETICAL` everywhere it appears.
2. **No forecast claim.** No hypothetical temperature/rainfall adjustment may be
   described as a NASA forecast, prediction or measurement.
3. **No scores.** Phase 6 must not introduce an arbitrary 0–100 score or weighted
   ranking. Comparisons report the recorded evidence and the explicit differences.
4. **Missing stays missing.** A scenario applied to an indicator with missing inputs
   stays missing; the engine reports which inputs were unavailable.
5. **Reproducibility.** Same inputs + same engine version ⇒ byte-identical output and
   the same SHA-256 of the input snapshot.
6. **Approved sources only.** NASA POWER remains the only environmental source. Crop
   traits remain gated by the Phase 5 catalogue. NLCD, MODIS land cover and any new
   dataset are **out of scope** for Phase 6.
7. **Owner scoping.** Simulation runs are farm-owned; cross-user access is `404`.
8. **No destructive change.** Phase 6 adds models/routes; it does not rewrite Phase 4
   or Phase 5 contracts or historical migrations.

## 3. Proposed slices

### 6.1 Scenario contract (docs + serializer only)

- Define the request contract: `scenario_mode`, `planning_seasons`, checkpoint list,
  and bounded adjustments (`temperature_delta_c`, `rainfall_multiplier` or equivalent).
- Document bounds and the exact wording used to mark values hypothetical.
- No persistence yet; validate the contract with serializer tests.

**Exit:** contract reviewed and merged; no simulation result can be produced yet.

### 6.2 Pure deterministic simulator

- A pure function over: baseline evidence digest, scenario definition, engine version.
- Emits checkpoints (Present, +6 months, +1 year, +2 years) mapped to **actual
  selected-region seasons**, preserving real calendar dates on every step.
- Every step lists: inputs used, inputs missing, applied adjustment, and the reason a
  value is unavailable.
- Unit tests cover zero adjustment (identity ⇒ baseline), bounds rejection, missing
  inputs, and reproducibility.

**Exit:** pure tests green; no API.

### 6.3 Persistence and API

- `SimulationRun` + `SimulationStep` models and migration (additive).
- `POST /api/v1/farms/{farm_id}/simulations/`,
  `GET /api/v1/simulations/{id}/`,
  `GET /api/v1/simulations/{id}/steps/`.
- Persist the input snapshot, scenario definition, engine version and SHA-256.
- Owner-scoped, authenticated; anonymous `401`, cross-user `404`.
- Reject requests that need a regional calendar that is not approved.

**Exit:** API contract tests green, including ownership and reproducibility.

### 6.4 Strategy comparison

- Compare `BASELINE`, `DRY_SCENARIO`, `HOT_SCENARIO`, `WATER_EFFICIENT`,
  `SOIL_REGENERATION` as **recorded scenario definitions**, not ranked outcomes.
- Show what differs and what is unsupported; never declare a winner.

**Exit:** comparison output contains no score, rank or recommendation claim.

### 6.5 Frontend scenario explorer

- Consume the real contract via `src/api`; no mocked result presented as live data.
- Show hypothetical labels, missing inputs, stale evidence and limitations.
- Tests for loading, empty, partial, error and stale states.

**Exit:** component tests, lint, TypeScript and production build green.

### 6.6 Verification gate

- Full backend suite, `manage.py check`, `makemigrations --check --dry-run`.
- Full frontend suite, lint, production build.
- Documented evidence in `docs/PHASE_6_STATUS.md`.

## 4. Acceptance criteria (Phase 6 overall)

- Changing a scenario input produces an explainably different result.
- No UI/API string labels a hypothetical adjustment as a NASA forecast.
- Same inputs and engine version produce the same output and SHA-256.
- Missing environmental evidence is reported, never filled.
- No numeric score, ranking, yield or profit estimate is introduced.

## 5. Dependencies and blockers

| Dependency | State |
|---|---|
| Approved Gharbia crop catalogue + season calendar | **Missing** — blocks meaningful crop-level comparisons |
| Phase 5 review gate (`approval_status`) | **Enforced** (see `PHASE_5_STATUS.md` §4) |
| Phase 4 release-gate audit (`PHASE_4_RELEASE_AUDIT.md`) | Verdict recorded: CONDITIONAL (release activities outstanding) |
| NASA POWER observations for the selected farm | Required for any environmental baseline |

Until the calendar exists, Phase 6 may compute and display environment-only scenario
summaries, but must not imply crop-level outcomes.

## 6. Explicit non-goals

- GPM IMERG or any new precipitation source.
- MODIS/NLCD land-cover integration.
- New crop traits or cultivar-level data.
- Yield, profit or soil-carbon modelling.
- Automatic recommendations or "best strategy" claims.

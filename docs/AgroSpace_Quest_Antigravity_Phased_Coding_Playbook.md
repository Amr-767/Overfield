# AgroSpace Quest — Antigravity Phased Coding Playbook

**Purpose:** A practical, copy-and-paste workflow for building AgroSpace Quest in Google Antigravity with Claude Opus 4.6 and a lower-cost model for routine tasks.

**Primary project brief:** `AgroSpace_Quest_Master_Agent_Handoff.md`

**Product:** AgroSpace Quest: The Elemental Balance  
**NASA challenge:** 2026 — Field Shift: Adapting Farms with NASA Data  
**Core stack:** Django + Django REST Framework + PostgreSQL/PostGIS + React

---

# 1. The most important rule

**Do not ask the agent to build the entire application in one prompt.** Build one working vertical slice at a time. Each phase must leave the repository in a working, testable state and update the project status files before the agent stops.

The Master Agent Handoff is the long-term project context. This playbook contains the execution order and prompts. The agent should not regenerate the specification every time it starts a new task.

## What success looks like

The first complete prototype should allow a farmer to:

1. Register and create a farm.
2. Select a location and draw or submit a farm boundary.
3. Enter basic soil information, current crops, available water, and farming priorities.
4. Request an environmental scan using at least one working NASA data integration.
5. See clearly labeled environmental indicators with source and freshness information.
6. Compare the existing crop rotation with at least two alternative strategies.
7. See why each strategy was suggested, the evidence used, its trade-offs, missing information, and local-review warnings.
8. Explore a clearly labeled scenario simulation.
9. Save a chosen strategy and record a seasonal check-in.

Leaderboard, rewards, partner integrations, and advanced automated verification are secondary. They must not delay the working agricultural decision-support journey.

---

# 2. Before opening Antigravity: prepare the workspace

## 2.1 Create or open the project folder

Create a clean project folder, for example:

```text
AgroSpaceQuest/
```

Open that folder as the Antigravity workspace. Do not start by asking the agent to create files in a random location.

## 2.2 Add the master project brief

Copy the attached file `AgroSpace_Quest_Master_Agent_Handoff.md` into the project folder under:

```text
AgroSpaceQuest/
└── docs/
    └── AgroSpace_Quest_Master_Agent_Handoff.md
```

If the `docs` folder does not exist, create it.

The master handoff is the main source of project context. Keep it in the workspace so the agent can refer to it in every phase without you repeatedly attaching the same large file.

## 2.3 Add this playbook

Copy this file into:

```text
AgroSpaceQuest/
└── docs/
    └── AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md
```

## 2.4 Add the visual references only when needed

Do not attach every image or design reference to every coding task.

For the frontend design phase, place the selected UI screenshots/mockups in:

```text
AgroSpaceQuest/
└── docs/
    └── design-reference/
```

Attach only the selected references and tell the agent what each image represents. Avoid attaching several contradictory mockups. The design references must not override the main agricultural requirements in the Master Handoff.

## 2.5 Initialize Git before substantial coding

Ask the agent to inspect whether Git is already initialized. If not, initialize it. Use a development branch, for example:

```bash
git init
git checkout -b develop
```

The agent should not commit secrets, `.env` files, API keys, credentials, or downloaded datasets. Add a `.gitignore` before creating local environment files.

If you already have a repository, do not reinitialize it. Ask the agent to inspect the existing branches and working tree first.

---

# 3. Files that must be maintained throughout development

Ask the agent to create and update these files. They are the memory system for the project between conversations and quota resets.

```text
AgroSpaceQuest/
├── docs/
│   ├── AgroSpace_Quest_Master_Agent_Handoff.md
│   ├── AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md
│   ├── PROJECT_STATUS.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── API_CONTRACTS.md
│   ├── DATA_PROVENANCE.md
│   └── design-reference/
├── backend/
├── frontend/
├── .gitignore
├── .env.example
└── README.md
```

### What belongs in each file

- `PROJECT_STATUS.md`: completed work, current phase, commands to run, tests run, known bugs, blockers, and the exact next task.
- `DEVELOPMENT_PLAN.md`: phases, dependencies, task breakdown, and acceptance criteria.
- `ARCHITECTURE_DECISIONS.md`: important decisions and why they were made. Use short Architecture Decision Records (ADRs).
- `API_CONTRACTS.md`: actual endpoint paths, methods, request/response examples, authentication, and error formats. Keep it aligned with the implementation.
- `DATA_PROVENANCE.md`: NASA and local data sources, exact product/variable, units, spatial/temporal support, time range, retrieval date, quality flags, processing steps, and known limitations.
- `.env.example`: names of required environment variables with placeholder values only. Never place real secrets here.
- `README.md`: setup, environment variables, migrations, running backend/frontend, background workers, tests, and troubleshooting.

At every phase boundary, the agent must update `PROJECT_STATUS.md`, `API_CONTRACTS.md` if APIs changed, `DATA_PROVENANCE.md` if data sources changed, and `ARCHITECTURE_DECISIONS.md` if an architectural decision was made.

---

# 4. How to run each phase in Antigravity

For every phase:

1. Open the existing AgroSpaceQuest workspace.
2. Select the requested model. Use Opus for architecture, difficult data/algorithm work, and complex debugging. Use a lower-cost available model for routine CRUD, forms, straightforward UI, and simple tests.
3. Start a fresh task/conversation for the phase if the current thread has become long or confused. The project files are the persistent context.
4. Paste the phase prompt below. Do not paste all phase prompts at once.
5. Let the agent inspect the repository before editing.
6. Review its plan and file changes. Do not approve broad destructive changes without understanding them.
7. Ask it to run the phase's acceptance tests.
8. Require a concise completion report and status-file updates.
9. Review the Git diff. Commit the working milestone yourself or ask the agent to commit after you have reviewed it.
10. Move to the next phase only when the current phase's acceptance criteria are satisfied or explicitly recorded as deferred.

**Important:** Antigravity may have different model and quota availability at different times. Choose the model from the model selector available in your account. Do not assume a model listed in an older document is still available.

---

# 5. Global instruction to prepend to every phase

Paste this short instruction before the phase-specific prompt, especially when starting a new conversation:

```text
You are working inside the existing AgroSpaceQuest repository.

Before doing anything, read:
- docs/AgroSpace_Quest_Master_Agent_Handoff.md
- docs/AgroSpace_Quest_Antigravity_Phased_Coding_Playbook.md
- docs/PROJECT_STATUS.md, if it exists
- docs/ARCHITECTURE_DECISIONS.md, if it exists
- docs/API_CONTRACTS.md, if it exists

Follow the Master Handoff's source-of-truth order and scientific accuracy requirements.
The core product is an explainable crop-rotation decision-support tool, not merely a game dashboard.

Work ONLY on the phase specified below. Do not start later phases or implement unrelated features.
Inspect the current code before editing. Preserve working behavior. Do not replace or reorganize large parts of the repository without explaining why and obtaining my approval.

Use official, current documentation for framework and NASA dataset details. Never invent an API endpoint, dataset resolution, revisit interval, variable, unit, or scientific capability. Distinguish observations, estimates, simulations, and forecasts.

Write maintainable code, add relevant tests, run them, fix failures, and report anything you could not verify. Never claim a test passed unless you ran it and observed the result.

At the end, update the relevant project documentation, especially docs/PROJECT_STATUS.md. Report changed files, commands run, test results, known limitations, and the exact next recommended task. Then STOP and wait for the next phase.
```

---

# 6. Phase 0 — Repository audit and implementation plan

**Model:** Claude Opus 4.6  
**Attach:** Master Handoff and this Playbook. If the repository already contains code, the code is available through the workspace; do not upload duplicate copies unless Antigravity cannot access them.  
**Code changes:** No application code in this phase.

## Prompt 0 — Planning only

```text
[Paste the Global Instruction first.]

PHASE 0: REPOSITORY AUDIT AND IMPLEMENTATION PLAN — DO NOT IMPLEMENT FEATURES YET.

Read the complete project brief and inspect the current workspace. Determine whether the repository is empty, partially implemented, or already contains an application.

Deliver the following:

1. A concise summary of the challenge-critical product and the MVP journey.
2. An audit of the existing repository: languages, framework versions, folder structure, dependencies, current features, tests, and obvious problems.
3. A proposed architecture that fits the current repository. Do not force a rewrite if a sound structure already exists.
4. A dependency-aware implementation plan divided into phases.
5. A recommended demonstration region. Do not silently assume global agricultural coverage. If no region has been selected, mark it as a decision that the team must make; use Egypt/Nile Delta/Gharbia only as a candidate, not as an established fact.
6. A dataset plan for the MVP. Recommend the smallest honest NASA data combination that can be implemented and explained during the hackathon. Identify exact NASA products and official documentation that must be checked.
7. A list of risks, unknowns, and decisions that could block development.
8. Acceptance criteria for every phase.
9. A recommended Git strategy and local development setup.

Create or update:
- docs/PROJECT_STATUS.md
- docs/DEVELOPMENT_PLAN.md
- docs/ARCHITECTURE_DECISIONS.md

Do not write backend or frontend feature code. Do not create fake NASA data or placeholder API responses and describe them as real data. Do not start Phase 1.

End with a prioritized list of the decisions I need to confirm and the exact Phase 1 task. STOP.
```

### Phase 0 completion check

You should have a realistic plan, a confirmed or explicitly unresolved demonstration region, a dataset shortlist, and no unnecessary application code.

---

# 7. Phase 1 — Project foundation and local development environment

**Model:** Use a lower-cost model for setup; use Opus only if a difficult architecture issue appears.  
**Attach:** Master Handoff. The Playbook stays in the workspace.  
**Code changes:** Yes, but foundation only.

## Prompt 1 — Foundation

```text
[Paste the Global Instruction first.]

PHASE 1: PROJECT FOUNDATION.

Implement only the project foundation approved in docs/DEVELOPMENT_PLAN.md.

Tasks:
1. Set up or repair the Django backend and React frontend according to the repository audit.
2. Configure PostgreSQL. Prepare PostGIS support if the development environment supports it; verify the installed PostgreSQL/PostGIS versions and document the setup rather than assuming an extension is available.
3. Configure Django settings safely for development and production separation.
4. Add environment-variable loading and create .env.example with placeholders only.
5. Configure CORS/CSRF appropriately for local frontend-backend development.
6. Add a basic health endpoint and a minimal React-to-Django connectivity check.
7. Configure formatting, linting, and basic automated tests where appropriate.
8. Add a useful .gitignore and README setup instructions.
9. If Celery/Redis is part of the approved architecture, add the minimal configuration and a test task, but do not build NASA ingestion yet.
10. Add API versioning conventions, such as /api/v1/, without prematurely creating all feature endpoints.

Constraints:
- Do not build farm, crop, NASA, recommendation, dashboard, leaderboard, or reward features yet.
- Do not expose secrets in code or logs.
- Avoid installing packages that are not needed for this phase.
- Check official documentation for the chosen framework versions and use compatible versions.

Acceptance criteria:
- Backend starts using documented commands.
- Frontend starts using documented commands.
- Backend health endpoint responds successfully.
- Frontend can call the health endpoint.
- Database connection works.
- Migrations run successfully.
- Automated starter tests pass.
- README contains reproducible setup instructions.

Update PROJECT_STATUS.md and stop after reporting the results. Do not start Phase 2.
```

### Phase 1 completion check

Run the backend and frontend yourself. Verify the health check in the browser or API client. Confirm the database is actually connected, not merely configured in a settings file.

---

# 8. Phase 2 — Accounts, farms, geospatial boundaries, and farmer onboarding inputs

**Model:** Opus for spatial design if needed; lower-cost model for routine CRUD and forms.  
**Attach:** Master Handoff. Attach one selected map/UI reference only if you already have a chosen design.  
**Code changes:** Backend models/APIs and basic frontend flow.

## Prompt 2 — Farm and geospatial module

```text
[Paste the Global Instruction first.]

PHASE 2: ACCOUNTS, FARM MANAGEMENT, GEOSPATIAL BOUNDARIES, AND FARMER INPUTS.

Implement the farm onboarding foundation only.

Backend requirements:
1. Implement user/profile functionality appropriate to the current authentication architecture. Do not overbuild social login or enterprise identity features.
2. Create Farm and, if justified by the requirements, FarmZone models.
3. Store farm boundaries with GeoDjango PolygonField or MultiPolygonField using an explicitly documented SRID.
4. Accept and validate GeoJSON through DRF. Reject malformed, empty, unsupported, or invalid geometries with useful errors.
5. Explain and implement accurate area calculation using an appropriate geodesic or PostGIS geography approach. Do not calculate acreage by treating longitude/latitude degrees as planar meters.
6. Add spatial indexes and ownership permissions. A user must not read or change another user's farms.
7. Support a farm location/centroid and optional zones. Do not automatically split farms just because they are large. Explain when zones are useful.
8. Add models or structured inputs for basic soil information, available water/irrigation, current crop rotation, farmer priorities, and practical constraints. Avoid adding every advanced soil attribute if the MVP does not collect it.

Frontend requirements:
1. Implement the minimum farm creation flow.
2. Let the user select a location and draw a polygon using the selected mapping library, if configured.
3. Show the boundary and calculated area before submission.
4. Provide a fallback path if polygon drawing is not ready: selected point plus farmer-entered area, clearly labeled as lower spatial precision.
5. Submit GeoJSON to the backend and show validation messages.

Tests:
- Valid polygon accepted.
- Invalid polygon rejected.
- Area calculation returns a plausible result for a known test geometry.
- Ownership permissions prevent cross-user access.
- Farm creation and retrieval work through the real API.
- Frontend successfully submits and displays a farm.

Document the API contracts and geometry assumptions. Do not integrate NASA data or build recommendation logic in this phase. Update PROJECT_STATUS.md and stop.
```

### Phase 2 completion check

Create a farm through the frontend, reload the page, and confirm that its boundary and area are retrieved from the database. Test access control using two separate users.

---

# 9. Phase 3 — NASA data providers and asynchronous ingestion

**Model:** Claude Opus 4.6. This is a high-value research and integration phase.  
**Attach:** Master Handoff. If the agent cannot browse official documentation, also provide official NASA product/API documentation links or downloaded technical references. Do not attach large raw satellite datasets unless the task specifically requires them.  
**Code changes:** Provider adapters, task queue, ingestion jobs, data-source records.

## Prompt 3 — NASA integration

```text
[Paste the Global Instruction first.]

PHASE 3: NASA DATA PROVIDERS AND ASYNCHRONOUS INGESTION.

Implement a small, real, verifiable NASA data-ingestion foundation. Do not attempt to integrate every dataset in the master brief.

Before coding:
1. Research the exact NASA product/service selected for each integration using official documentation.
2. Verify the current endpoint or access mechanism, variables, units, temporal coverage, spatial support/resolution, response format, authentication requirements, and licensing/access conditions.
3. Record exact source URLs and access date in docs/DATA_PROVENANCE.md.
4. If a detail cannot be verified, state that explicitly and do not invent it.

MVP target:
- Implement NASA POWER as the first climate-data provider if confirmed suitable by the research.
- Implement one additional useful dataset only if it can be integrated reliably within scope (GPM precipitation or another well-justified product are candidates).
- Treat SMAP or ECOSTRESS as optional context unless exact product access and spatial/temporal limitations are understood.

Architecture requirements:
1. Create provider adapters so the recommendation engine does not call NASA services directly.
2. Add data-source/dataset metadata and ingestion-job records.
3. Use Celery/Redis for slow retrieval if the foundation supports it.
4. Implement task states: queued, running, succeeded, partially_succeeded, failed.
5. Add timeout, bounded retry, backoff, and useful error logging.
6. Make ingestion idempotent. Repeating the same request must not create duplicate observations.
7. Keep API credentials on the backend, never in React.
8. Store normalized observations and provenance in PostgreSQL. Store large raster files outside ordinary relational fields, with metadata/references in the database.
9. Do not make dashboard requests wait synchronously for a full external data download.
10. Provide a scan-status API and a way for React to retrieve the result when ready.

Testing requirements:
- Unit-test provider parsing with representative fixtures.
- Test units and missing values.
- Test timeout and provider-failure behavior.
- Test duplicate-ingestion prevention.
- Use mocked external responses in automated tests; keep at least one documented manual integration test for real NASA access.
- Never label mocked fixtures as live NASA observations.

Do not implement the recommendation engine, future simulations, leaderboard, or rewards. Update DATA_PROVENANCE.md, API_CONTRACTS.md, and PROJECT_STATUS.md. Stop after this phase.
```

### Phase 3 completion check

Run one real NASA request for the chosen test farm or coordinates. Verify the raw response, normalized data, units, timestamps, source metadata, and error handling. Keep mocked tests separate from the real integration test.

---

# 10. Phase 4 — Environmental indicators and data fusion

**Model:** Claude Opus 4.6 for feature design and uncertainty; lower-cost model for implementation after the design is accepted.  
**Attach:** Master Handoff and the current `DATA_PROVENANCE.md`.  
**Code changes:** Indicator services, snapshot models, environmental summary APIs, map-layer preparation if feasible.

## Prompt 4 — Environmental processing

```text
[Paste the Global Instruction first.]

PHASE 4: ENVIRONMENTAL INDICATORS, DATA QUALITY, AND DATA FUSION.

Build the processing layer on top of the NASA/local data that is genuinely available in the repository. Do not assume a dataset exists merely because it appears in the project brief.

Implement:
1. A normalized internal representation for environmental variables, with value, unit, timestamp/period, source dataset, spatial support, quality information, and provenance.
2. Farm-level or zone-level aggregation that respects the source product's native spatial support.
3. Temporal aggregation suitable for agricultural summaries, documenting each window.
4. Derived indicators that are supportable by the available inputs, for example temperature summaries, precipitation totals, dry-spell indicators, soil-moisture context, or vegetation indices if the underlying dataset is actually integrated.
5. A data-quality and freshness status for each indicator: available, stale, partial, missing, or low_quality.
6. Explicit distinction between observed values, derived estimates, user-provided values, and scenario outputs.
7. Missing-data handling. Do not replace missing values with zero or silently invent data.
8. Unit conversion and validation.
9. A FarmEnvironmentalSnapshot or equivalent response model to make frontend retrieval efficient.
10. A summary API that returns indicator values, units, labels, observation periods, source, quality/freshness, and limitations.

Scientific constraints:
- Do not claim that satellites directly measured soil nitrogen, phosphorus, pH, or organic matter unless a real, validated source supports that exact claim.
- Do not assign a fine farm-level resolution to a coarse satellite product.
- Do not upsample coarse data and imply that it gained real spatial detail.
- Do not describe NASA POWER historical/near-real-time values as future forecasts.
- Clearly explain satellite observations versus ground measurements.

Tests:
- Unit and conversion tests.
- Aggregation tests using known fixtures.
- Missing/stale/low-quality status tests.
- Provenance preservation tests.
- API response contract tests.

Do not build the crop recommendation engine or visual dashboard in this phase. Update DATA_PROVENANCE.md, API_CONTRACTS.md, and PROJECT_STATUS.md. Stop.
```

### Phase 4 completion check

Inspect API responses and confirm every displayed environmental value has a unit, source, period, and quality/freshness label. Make sure missing data is visibly missing rather than fabricated.

---

# 11. Phase 5 — Crop knowledge base and recommendation engine

**Model:** Claude Opus 4.6. This is one of the most important reasoning-heavy phases.  
**Attach:** Master Handoff, `DATA_PROVENANCE.md`, and the current crop/soil/region sources that the team has verified. If no local agronomic source is available, instruct the agent to create clearly marked seed data for the demo and record that it needs expert validation.  
**Code changes:** Crop models/catalog, regional calendars, agronomic rules, deterministic recommendation service, tests.

## Prompt 5 — Agricultural recommendation engine

```text
[Paste the Global Instruction first.]

PHASE 5: REGIONAL CROP KNOWLEDGE BASE AND EXPLAINABLE ROTATION RECOMMENDATION ENGINE.

This is the core agricultural intelligence. Design and implement a deterministic, explainable MVP. Do not train a machine-learning model without suitable representative training data.

First inspect the actual region, crop inputs, local calendar, environmental indicators, and soil information available in the project. Do not invent local crop facts. Mark illustrative seed data clearly and record sources/validation status.

Implement a configurable crop knowledge base containing only the fields justified by the current scope, with a path to expand:
- crop name and scientific name where available;
- crop family;
- regional growing season and planting/harvest windows;
- crop duration;
- water demand or requirement category;
- heat/drought/frost suitability where supported;
- rooting characteristics where sourced;
- nitrogen-fixation potential for relevant legumes;
- residue/cover-crop/organic-matter contribution estimates where sourced;
- forage value;
- nutrient demand/uptake assumptions where supported;
- pest/disease rotation relationships;
- market suitability and market-data source;
- data source and validation status.

Recommendation pipeline:
1. Validate farmer and farm inputs.
2. Apply hard eligibility constraints (season, climate, soil, water, critical local constraints).
3. Apply soft preferences (water saving, soil regeneration, market, forage, equipment, labor, seed availability).
4. Generate valid multi-season sequences over a configurable horizon.
5. Enforce configurable crop-family and pest-cycle constraints.
6. Evaluate each sequence for water demand, heat/climate suitability, soil regeneration potential, nutrient cycling, erosion-related factors where supportable, crop diversity, forage, market, and farmer priorities.
7. Normalize criteria using documented methods and configurable weights.
8. Generate the existing rotation as the baseline plus at least two alternatives.
9. Return rationale, benefits, trade-offs, missing data, risks, confidence/coverage information, and evidence references for every strategy.

The game-facing strategy names may be:
- Traditional Path — existing practice/baseline.
- Hydra Shield — water-saving objective.
- Nitrogen Battery — soil-regeneration objective.

These are objective labels, not fixed crop sequences. The selected crops must come from eligibility and scoring.

Important:
- Do not claim modeled nitrogen fixation equals measured soil nitrogen change.
- Do not guarantee yield or profit without a validated model and data.
- Separate hard constraints from weighted preferences.
- Show how missing inputs reduce confidence or make a criterion unavailable.
- Do not disguise arbitrary score weights as scientifically measured truths.
- Include a farmer-readable explanation and a machine-readable evidence structure.

Deliver:
- Database models and serializers where needed.
- A framework-independent recommendation service.
- Unit tests for eligibility, season sequencing, family constraints, scoring, missing data, and baseline comparisons.
- At least one transparent example using clearly labeled demo data.
- API request/response examples and updates to API_CONTRACTS.md.

Do not build the full visual game dashboard, verification, rewards, or leaderboard yet. Update PROJECT_STATUS.md and stop.
```

### Phase 5 completion check

Use a known test farm and inspect all three strategies. Confirm the baseline is the farmer's actual input, alternatives are valid for the selected region/calendar, and every recommendation has a defensible explanation and evidence trail.

---

# 12. Phase 6 — Scenario simulation and strategy comparison

**Model:** Claude Opus 4.6 for simulation assumptions and backend design; lower-cost model for routine UI wiring.  
**Attach:** Master Handoff, current recommendation-engine documentation, and `DATA_PROVENANCE.md`.  
**Code changes:** Scenario models/service/APIs, comparison responses, basic timeline integration.

## Prompt 6 — Future Time Portal

```text
[Paste the Global Instruction first.]

PHASE 6: SCENARIO SIMULATION AND ROTATION COMPARISON.

Implement a transparent scenario engine for comparing the baseline, water-saving, and soil-regeneration strategies over the supported planning horizon.

Timeline nodes:
- Present Day.
- +6 Months.
- +1 Year.
- +2 Years.

The timeline values represent modeled scenario horizons, not guaranteed future observations.

Requirements:
1. Define explicit simulation inputs and assumptions.
2. Support user-adjustable temperature and rainfall scenarios only within documented, reasonable bounds. If an external forecast provider is not integrated, label them as hypothetical scenario adjustments, not forecasts.
3. Re-evaluate crop eligibility and seasonal sequence under the scenario assumptions.
4. Estimate changes using transparent crop/rotation coefficients and rules already stored in the knowledge base.
5. Return outputs separately for observed baseline, modeled estimates, and hypothetical scenario results.
6. Include uncertainty/coverage warnings and sensitivity to assumptions.
7. Store scenario version, input values, model/rule version, run time, and results so a result can be reproduced.
8. Compare all three strategies using consistent assumptions.
9. Return a clear explanation of why each gauge or metric changes.
10. Support a map overlay only where spatial input and data resolution justify it.

The four dashboard indicators are composite decision-support indicators, not direct measurements. Do not imply a two-year projection is a precise prediction of soil or yield outcomes.

Add:
- Scenario and SimulationRun models as needed.
- A clean simulation service independent of DRF.
- Background execution only if computation is slow enough to justify it.
- API endpoints for creating, running, checking, and retrieving simulations.
- Tests for deterministic reproducibility, invalid scenario ranges, missing inputs, and strategy comparability.

Do not implement automated satellite verification, partner rewards, or leaderboard changes in this phase. Update API_CONTRACTS.md and PROJECT_STATUS.md. Stop.
```

### Phase 6 completion check

Change a scenario input and confirm results change for an explainable reason. Confirm the UI/API never labels a hypothetical temperature/rainfall adjustment as a NASA forecast.

---

# 13. Phase 7 — Farmer-facing React experience and dashboard

**Model:** Lower-cost available model for most UI coding; Opus for complex state/data-flow decisions.  
**Attach:** Master Handoff and only the chosen screenshots/mockups from `docs/design-reference/`.  
**Code changes:** Main screens, reusable components, map and chart/visual layers, API integration.

## Prompt 7 — Frontend experience

```text
[Paste the Global Instruction first.]

PHASE 7: FARMER-FACING REACT EXPERIENCE.

Build the frontend around the real APIs and data contracts already implemented. Do not invent frontend-only fake production data to make the screens appear complete. Clearly labeled demo fixtures are acceptable only in an isolated demo mode.

The experience should be visually engaging, welcoming, and easy for farmers to understand, but not childish. Use the selected design references in docs/design-reference/ as visual guidance only. Prioritize clarity, accessibility, readable Arabic/English localization if the project scope requires it, mobile responsiveness, and understandable agricultural language.

Implement the following journey:
1. Welcome / initialize mission.
2. Create or select a farm.
3. Draw/select farm boundary and show area.
4. Enter current crop routine, basic soil details, water availability, and farmer priorities/constraints.
5. Start environmental scan and show queued/running/success/partial/failure states.
6. Show baseline environmental summary with source, unit, period, freshness, and confidence/limitations.
7. Show the three strategy cards: Traditional Path, Hydra Shield, Nitrogen Battery.
8. Explain why each strategy was recommended, its potential benefits, trade-offs, data gaps, and need for local review.
9. Add the timeline controls and display backend simulation results.
10. Show the four elemental gauges as clearly labeled composite indicators, with accessible explanations and confidence/quality states.

Implementation guidance:
- Build reusable API client functions.
- Centralize authentication and error handling.
- Handle loading, empty, partial, stale, and failed states.
- Do not store secrets or call NASA APIs directly from the browser.
- Avoid hardcoded business logic that duplicates the backend recommendation engine.
- Use responsive layouts and keyboard-accessible controls.
- Use map drawing tools only if the backend geometry API is working.
- Keep charts and numerical details secondary to clear farmer-oriented explanations.

Test the complete flow from the UI against the local backend. Update README and PROJECT_STATUS.md. Do not add leaderboard/reward features in this phase. Stop.
```

### Phase 7 completion check

A user should be able to complete the full farm-to-recommendation-to-simulation journey without manually editing database records or using API tools.

---

# 14. Phase 8 — Strategy commitment, check-ins, score, leaderboard, and rewards mockup

**Model:** Lower-cost model for CRUD/UI; Opus for verification logic and scientific review.  
**Attach:** Master Handoff and current API contracts.  
**Code changes:** Check-in and ledger APIs, frontend interactions, demo leaderboard, reward mockup.

## Prompt 8 — Engagement and verification

```text
[Paste the Global Instruction first.]

PHASE 8: STRATEGY COMMITMENT, SEASONAL CHECK-INS, GAMIFICATION, AND REWARD MOCKUP.

Implement the prototype portion only. Do not build a commercial payment or real subsidy-redemption system.

Build:
1. Commit a selected crop strategy and retain a versioned copy of the selected plan and its assumptions.
2. Seasonal action log/check-in records linked to the committed plan.
3. A status such as pending_review, self_reported, expert_reviewed, or supported_by_observation, with clear definitions.
4. A points ledger with auditable positive/negative adjustments and reasons. Do not store only a mutable total.
5. Basic badges and a regional leaderboard using privacy-conscious public display names.
6. A static or clearly labeled demo reward recommendation panel.
7. A future partner/reward data model only if it does not delay or destabilize the core journey.

Critical verification constraints:
- A farmer click is a self-reported action, not proof that the action occurred.
- A change in SMAP soil moisture does not prove that irrigation occurred or that a specific farmer caused the change.
- Missing or inconclusive satellite data must not punish the farmer.
- The 80% score cap, if used, is a game rule, not scientific confidence or agricultural certification.
- Expert review must be clearly distinguished from automated evidence.

Add ownership/security tests, score-ledger tests, duplicate check-in protection, and tests that missing satellite data cannot automatically reduce a user's score. Update API_CONTRACTS.md and PROJECT_STATUS.md. Stop.
```

### Phase 8 completion check

Submit a check-in and verify that it is labeled as self-reported or pending—not satellite-confirmed. Confirm score history is auditable and missing data cannot unfairly penalize the user.

---

# 15. Phase 9 — Full integration, security, testing, and demo readiness

**Model:** Claude Opus 4.6 for review and complex debugging; lower-cost model for mechanical fixes.  
**Attach:** Master Handoff, all project tracking files, and any judge/demo requirements that have changed.  
**Code changes:** Fixes only; no uncontrolled new features.

## Prompt 9 — Final integration audit

```text
[Paste the Global Instruction first.]

PHASE 9: FULL INTEGRATION, SECURITY, TESTING, AND DEMO READINESS.

Do a systematic audit of the implemented application against the Master Handoff and the official Field Shift challenge requirements.

Do not add new major features. Identify and fix defects in the existing scope.

Audit these areas:
1. Complete farmer journey from account/farm creation through recommendations, simulation, strategy commitment, and check-in.
2. Backend/frontend API contract consistency.
3. Database migrations, indexes, foreign keys, ownership, and spatial validation.
4. NASA provider accuracy, source documentation, data units, provenance, quality flags, and missing-data behavior.
5. Separation of observation, user input, estimate, simulation, and forecast.
6. Crop eligibility, seasonal validity, family/pest constraints, and baseline comparison.
7. Explainability: every strategy has rationale, benefits, risks, missing information, and evidence.
8. Correct interpretation of the four composite gauges.
9. Scenario assumptions and repeatability.
10. Authentication, authorization, secret handling, CORS/CSRF, input validation, throttling where appropriate, and logging.
11. Error/loading/empty/partial states in React.
12. Mobile responsiveness and accessibility for the key journey.
13. README, environment setup, migrations, worker startup, and demo instructions.

Run the relevant automated test suites and report exact commands and results. Do not claim success for tests that were not run. Identify tests that need live external access and keep them separate from deterministic automated tests.

Create or update:
- docs/PROJECT_STATUS.md
- docs/CHALLENGE_COVERAGE_AUDIT.md
- docs/DEMO_RUNBOOK.md
- README.md

The challenge coverage audit must map each challenge objective to the implemented feature, API/model/service, test or evidence, and known limitation. Mark incomplete items honestly.

Finish with:
- What's working end to end.
- What's only mocked/demo data.
- What's incomplete.
- Known scientific limitations.
- The exact commands to run the demo.
- A short demo script for judges.

Do not start another feature phase. Stop.
```

### Phase 9 completion check

Run the documented demo steps from a clean environment if possible. Do not rely on hidden local state, manually inserted database records, or unrecorded API keys.

---

# 16. How to switch models without losing context

You may use Opus for Phase 0, hard NASA research, crop-rotation logic, simulation assumptions, and final review. Use a cheaper model for routine CRUD, standard React components, documentation updates, and straightforward tests.

When switching models:

1. Stay in the same workspace.
2. Start a new task if the conversation context has become long.
3. Tell the new agent to read `PROJECT_STATUS.md`, `ARCHITECTURE_DECISIONS.md`, and `API_CONTRACTS.md` before coding.
4. Give it only one specific task.
5. Ask it to preserve existing contracts and run the relevant tests.

Use this model-switch prompt:

```text
Continue the existing AgroSpaceQuest project. Do not assume the previous conversation is available.

Read:
- docs/AgroSpace_Quest_Master_Agent_Handoff.md
- docs/PROJECT_STATUS.md
- docs/ARCHITECTURE_DECISIONS.md
- docs/API_CONTRACTS.md
- docs/DATA_PROVENANCE.md

Summarize the current implemented state, architecture constraints, failing tests/known issues, and the next task recorded in PROJECT_STATUS.md. Do not edit files yet. Wait for my task instruction.
```

---

# 17. How to avoid wasting Opus quota

1. Do not ask it to reread and summarize the whole project in every message. Keep the handoff file in the repository and ask it to inspect only the relevant sections for each task.
2. Give one bounded deliverable per prompt. Avoid "build everything" requests.
3. Ask for a plan before a risky or wide change. Review it before implementation.
4. Do not ask the agent to repeatedly rewrite project documentation that has not changed.
5. Run simple commands and inspect obvious UI behavior yourself where practical.
6. Use the lower-cost model for routine implementation and Opus for difficult reasoning.
7. Stop an agent when it starts expanding scope. Ask it to finish the phase acceptance criteria only.
8. Keep tests focused and deterministic. Use mocked external responses for routine tests; reserve live NASA calls for an explicit integration test.
9. Commit each working milestone so quota resets or model changes do not threaten progress.
10. If quota is nearly exhausted, ask for a handoff summary and status-file update rather than beginning a new large feature.

## Prompt to save progress before stopping

```text
Before stopping, do not start any new work. Update docs/PROJECT_STATUS.md with:
- Current phase and exact completion status.
- Files created or changed.
- What works and how to run it.
- Tests run and their actual results.
- Current errors and unresolved issues.
- Decisions made and why.
- Any uncommitted changes.
- The smallest exact next task to resume.

Also update API_CONTRACTS.md, DATA_PROVENANCE.md, and ARCHITECTURE_DECISIONS.md only if this task changed them.

Then give me a concise handoff summary so I can resume in a new conversation or with another model.
```

---

# 18. What to attach and when — quick reference

| Phase | Always available in workspace | Extra attachment only when needed |
|---|---|---|
| 0 — Audit | Master Handoff + Playbook | Existing repository files are accessed through workspace |
| 1 — Foundation | Master Handoff + status/plan | None normally |
| 2 — Farms/map | Master Handoff + API contracts | One selected map/UI reference |
| 3 — NASA integration | Master Handoff + provenance | Official product docs if browser research unavailable |
| 4 — Indicators | Master Handoff + provenance | Small representative sample data, if needed and licensed |
| 5 — Crop engine | Master Handoff + provenance | Verified regional crop calendars, soil/agronomy sources, crop data |
| 6 — Simulation | Master Handoff + API contracts + crop rules | Scenario assumptions supplied by the team, if any |
| 7 — Frontend | Master Handoff + API contracts | Selected design mockups/screenshots |
| 8 — Gamification | Master Handoff + API contracts | Final reward/leaderboard design, if available |
| 9 — Final audit | All project tracking docs | Official judging/submission requirements, if updated |

Do not attach raw passwords, API keys, credentials, private farmer records, or sensitive real farm data. Use synthetic/demo farm data unless you have permission to use real data.

---

# 19. Final rules for the team

- Keep the first implementation region-specific and configurable. Do not claim global agronomic validity just because the map accepts worldwide coordinates.
- Prioritize a complete end-to-end agricultural decision-support journey over an elaborate game interface.
- A farm boundary does not guarantee that satellite data resolves that farm at the same boundary scale.
- A successful HTTP response does not guarantee a scientifically suitable observation. Check product, units, time, quality, and spatial support.
- A scenario slider is not a weather forecast unless an actual forecast provider is integrated and identified.
- A self-reported action is not automatically verified.
- The model should explain recommendations and uncertainty, not invent agronomic facts.
- Never let the agent claim a feature works unless it has been tested through the actual API or user flow.

**Recommended starting action:** Put the Master Handoff and this Playbook in `docs/`, open the repository in Antigravity, select Claude Opus 4.6, and run Prompt 0 only. Review the plan before allowing Phase 1 coding.

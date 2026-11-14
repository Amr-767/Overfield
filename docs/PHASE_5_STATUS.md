# Overfield — Phase 5 Status

**Date:** 2026-11-14
**Branch:** `phase/5-rotation-engine`
**Scope:** Phase 5.1/5.2 crop-knowledge catalogue and Phase 5.3 fail-closed rotation
evidence engine.

This document records what Phase 5 actually implements, the verification evidence
produced in this checkout, the interpretations chosen to resolve two semantic test
failures, and the limitations that still block production recommendations.

---

## 1. What is implemented

| Area | Implementation |
|---|---|
| Agricultural dataset registry | `apps/agronomy/models.py` — `AgriculturalDataset` with explicit `PROPOSED` / `APPROVED` / `RETIRED` status, publisher, version, DOI, licence, attribution, and approval audit fields. |
| Import audit | `DatasetImport` / `DatasetResource` — checksum-keyed idempotent imports, per-row errors, `SUCCEEDED` / `PARTIAL` / `FAILED` / `SKIPPED` status. |
| Crop traits | `Crop`, `CropAlias`, `CropSourceIdentity`, `CropCharacteristic` — raw value, unit, normalized value/text/boolean, temporal and geographic scope, source record, evidence reference, revision chain, and an immutable source snapshot (dataset identity/version/licence). |
| Review flow | `ReviewRequest` + `apps/agronomy/reviews.py` — reviewer decisions set `approval_status`, `validation_status`, `approved_geographic_applicability` and `geographic_applicability`. |
| Regional calendar | `RegionAgronomyProfile`, `RegionSeason`, `RegionSeasonCrop`, `CropRotationRule` — sourced calendars and reviewed rotation constraints. |
| Rotation engine | `apps/agronomy/rotation.py` — pure deterministic evidence-readiness evaluation; no score, ranking weight, yield, profit, or soil-benefit claim. |
| Persistence | `RotationRecommendation` — input snapshot, engine version, SHA-256, assessment payload. |
| REST API | `GET /api/v1/crops/`, `GET /api/v1/crops/{id}/profiles/`, `GET /api/v1/regions/{region_code}/crop-calendar/`, `POST /api/v1/farms/{id}/recommendations/`, `GET /api/v1/recommendations/{id}/`, `.../compare/`, `.../explanation/`, `POST /api/v1/agronomy/reviews/`. All authenticated; farm endpoints owner-scoped. |
| Frontend | `frontend/src/pages/RotationExplorerPage.tsx` + `frontend/src/api/rotation.ts` — consumes the real summary and rotation contracts, displays missing/insufficient evidence honestly. |

The catalogue contains **no production crop traits and no Egyptian calendar**.
No individual USDA Ag Data Commons (or other) dataset has been approved in this
repository. Live rotation requests therefore return `INSUFFICIENT_EVIDENCE` with no
unsupported alternatives, which is the intended fail-closed behaviour.

## 2. Verification evidence (this checkout)

Run on 2026-11-14 against the Dockerized Django/PostGIS backend and the host Vite app.

| Command | Result |
|---|---|
| `python manage.py test tests` | **321 tests OK** (0 failures, 0 errors) |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `npm test -- --run` (frontend) | **61 passed** across 8 files |
| `npm run lint` (`oxlint`) | Clean |
| `npm run build` (`tsc -b && vite build`) | Succeeded (pre-existing >500 kB chunk warning) |
| `git diff --check` | Clean |

Phase 5-specific suites:

- `tests/test_agronomy.py` — import provenance, idempotency, missing values, unit
  validation, unapproved-dataset rejection, catalogue/profile API contract.
- `tests/test_rotation_engine.py` — pure engine: missing history, ambiguous history,
  baseline-only output, unsupported constraints, stale environment, conflicting inputs.
- `tests/test_rotation_api.py` — persistence, ownership, deterministic snapshot,
  compare/explanation endpoints.

## 3. Defects fixed while preparing this branch for publication

| # | Defect | Fix |
|---|---|---|
| 1 | `NameError: GeographicApplicability` — `ReviewRequest` referenced a `TextChoices` class defined later in the module, so the whole `agronomy` app failed to import. | Moved the enum above `ReviewRequest` in `apps/agronomy/models.py`. |
| 2 | Migration drift — models had fields/models with no migration (`CropAlias`, `CropSourceIdentity`, `ReviewRequest`, review/provenance fields, constraints, indexes). | Generated `apps/agronomy/migrations/0004_sync_phase5_models.py`. No historical migration was edited. |
| 3 | `KeyError: 'environmental_inputs'` — `RecommendationExplanationView` read a key that `recommendation_payload()` never emits (it emits `environmental_digest`). | The view now reads `payload["environmental_digest"]` and keeps the documented response key `environmental_inputs`. |

## 4. Interpretations chosen to resolve the two semantic failures

Both failures came from the importer deliberately discarding the source's own
`geographic_applicability` and `validation_status` claims and storing `UNKNOWN` /
`REVIEW_REQUIRED` on the effective fields. The Phase 5 tests treat the source claims
as the effective values. The following interpretation keeps the auditable separation
intact:

1. **`geographic_applicability` mirrors the source claim.** `imports.py` now stores
   `geo_claim` (falling back to `UNKNOWN`) in `geographic_applicability`, while
   `source_geographic_applicability_claim` retains the raw claim and
   `approved_geographic_applicability` stays `UNKNOWN` and `approval_status` stays
   `PENDING` until an authorized reviewer decides. Review decisions may overwrite
   `geographic_applicability` (`apps/agronomy/reviews.py`).
2. **`validation_status` mirrors the source validation claim.** `imports.py` now
   stores the mapped claim (falling back to `REVIEW_REQUIRED`) in `validation_status`.
   `approval_status` remains the independent review decision; nothing is auto-approved.

Rationale: the model already carries both the source-claimed value and the reviewer
decision in separate fields. Recording the claim is not the same as approving it, and
the provenance remains visible in the API response.

### Known consequence (documented, not hidden)

`apps/agronomy/recommendations.py::_eligible_profiles` currently gates on
`validation_status == VALID` and geographic applicability, **not** on
`approval_status == APPROVED`. Because a source may claim `VALID`, an unreviewed trait
can reach candidate profiles. Closing this requires a product decision (and a test
contract change) and is listed as a Phase 6 gate item — see §5.

## 5. Limitations and required follow-up

- **No approved production dataset or Gharbia calendar.** Recommendations remain
  `INSUFFICIENT_EVIDENCE`; no crop trait is invented.
- **Approval gating.** As above, the engine trusts a source's `VALID` claim. A future
  slice should require `approval_status == APPROVED` (or an explicit per-dataset
  waiver) before a trait is eligible.
- **No scores, no ranking.** The engine reports evidence readiness only. Any numeric
  suitability score would need a validated methodology and is intentionally absent.
- **No new datasets.** NLCD is U.S.-only and is not used for Gharbia; MODIS land cover
  is not integrated; no third-party crop database was added.
- **Frontend coverage.** The rotation explorer is component-tested with mocked
  transport. A live browser end-to-end run against the Docker stack is not automated.
- **Phase 4 release gate.** `docs/PHASE_4_RELEASE_AUDIT.md` is still owed a final
  verdict (see `docs/PROJECT_STATUS.md`).

## 6. Data-provenance statement

Every displayed crop trait is traceable to the dataset identifier, publisher,
version, licence, attribution, resource, source record identifier and evidence
reference captured at import time. Environmental inputs remain NASA POWER
reanalysis/grid-cell values, never field measurements. Missing evidence is reported
as missing; no value is substituted from another source or from a later date.

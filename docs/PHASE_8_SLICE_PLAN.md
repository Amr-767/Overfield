# Overfield — Phase 8 Scope, Architecture & Slice Plan

**Date:** 2026-11-14  
**Branch:** `phase/8-gamification-rewards` (branched from verified Phase 7 tip `0eddab5`)  
**Status:** In Progress (Phase 8 Startup)  

---

## 1. Phase 8 Overview & Objective

Phase 8 introduces **Strategy Commitment, Seasonal Action Logs / Check-ins, Gamification (Auditable Points Ledger & Badges), and Reward Mockup** as scoped in the Master Handoff and Phased Coding Playbook.

The objective is to allow a farmer to:
1. **Commit a selected agricultural adaptation strategy** (e.g. from the rotation or scenario workflows) and retain a versioned snapshot of the plan, including its evidence and assumptions.
2. **Record seasonal check-ins and action logs** against the committed strategy (e.g., planting date, cover crop sowing, irrigation adjustment).
3. **Earn points and achievements in an auditable ledger** with transparent positive/negative ledger records and reason codes.
4. **View regional leaderboards and badges** using privacy-preserving display handles.
5. **Explore local agricultural rewards and incentives** (vouchers, seed discounts, or recognition mockups) clearly marked as prototype/partner demonstrations.

---

## 2. Scientific & Ethical Verification Constraints

Under Overfield's core principles:
1. **Self-Reported vs. Observed Evidence**:
   - A farmer check-in is an assertion (`self_reported`), not satellite confirmation.
   - Status vocabulary must be explicit: `self_reported`, `pending_review`, `expert_reviewed`, `supported_by_observation`.
2. **No Data-Missing Penalties**:
   - Missing satellite observations or cloud cover must **never** penalize the farmer's score or ledger balance.
3. **Immutable Ledger**:
   - Never store only a single mutable balance column. Points must be computed from an append-only transaction ledger (`PointLedgerEntry`) with timestamp, reason code, reference object, and delta.
4. **No Financial Claims**:
   - Reward panels are mockups / partner demonstration points; no real-money disbursement or unverified subsidy claims.

---

## 3. Architecture & Data Model Slices

### Slice 8.1: Strategy Commitment & Versioning
- **Model `CommittedStrategy` (`apps.plans` or `apps.agronomy`)**:
  - `farm` (FK to `Farm`, CASCADE / PROTECT)
  - `author` (FK to `User`)
  - `status` (`ACTIVE`, `SUPERSEDED`, `COMPLETED`, `ARCHIVED`)
  - `plan_name`, `target_season`, `target_year`
  - `strategy_snapshot` (JSONField: snapshot of rotation/scenario candidate, rationale, indicators, parameters)
  - `committed_at`, `updated_at`

### Slice 8.2: Seasonal Check-ins & Action Logs
- **Model `SeasonalCheckIn`**:
  - `strategy` (FK to `CommittedStrategy`, related_name `check_ins`)
  - `farm` (FK to `Farm`)
  - `date`, `season`
  - `action_type` (e.g., `SOWING`, `IRRIGATION_EVENT`, `SOIL_AMENDMENT`, `COVER_CROP`, `HARVEST`)
  - `verification_status` (`SELF_REPORTED`, `PENDING_REVIEW`, `EXPERT_REVIEWED`, `SUPPORTED_BY_OBSERVATION`)
  - `notes` (text)
  - `evidence_metadata` (JSONField: photo link reference, observation window ID, or self-reported details)

### Slice 8.3: Auditable Points Ledger & Badges
- **Model `PointLedgerEntry`**:
  - `user` (FK to `User`)
  - `farm` (FK to `Farm`, nullable)
  - `points` (integer, signed)
  - `reason_code` (`PLAN_COMMITTED`, `CHECKIN_RECORDED`, `STREAK_BONUS`, `SEASON_COMPLETED`, etc.)
  - `reference_id`, `reference_type`
  - `created_at`
- **Model `Badge` / `UserBadge`**:
  - Predefined badges (`SOIL_STEWARD`, `WATER_CONSERVER`, `ADAPTATION_PIONEER`, etc.)
  - `awarded_at`

### Slice 8.4: Regional Leaderboard & Reward Mockups
- **Leaderboard API**:
  - Aggregates verified ledger points by region (e.g., `EG-GH`) using privacy-conscious handles (e.g., `Farmer-482` or user-chosen pseudonym).
- **Reward Catalog**:
  - Partner demonstration tier list (e.g., local extension service vouchers, biological fertilizer discounts). Clearly badged as `PROTOTYPE_PARTNER_MOCKUP`.

### Slice 8.5: Frontend Experience
- Strategy commitment confirmation modal from Rotation/Simulations.
- "My Plan" and "Seasonal Logbook" timeline page.
- Points, Badges, and Leaderboard components.

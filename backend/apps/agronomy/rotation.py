"""Deterministic, fail-closed crop-rotation assessment.

This module is deliberately independent of Django and the database. It does not
rank candidates or interpret unsupported crop traits. Until an approved
regional calendar and eligible source-backed profiles exist, it returns explicit
missing-evidence reasons instead of inventing a sequence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

ENGINE_VERSION = "rotation-v1.0"
STRATEGIES = ("BASELINE", "WATER_EFFICIENT", "SOIL_REGENERATION")


@dataclass(frozen=True, slots=True)
class RotationAssessment:
    status: str
    options: tuple[dict[str, Any], ...]
    missing: tuple[dict[str, str], ...]
    constraints: tuple[dict[str, Any], ...]
    environmental_inputs: tuple[dict[str, Any], ...]
    data_limitations: tuple[str, ...]
    rejected_alternatives: tuple[dict[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-ready collections rather than immutable tuples."""
        result = asdict(self)
        for key in ("options", "missing", "constraints", "environmental_inputs", "data_limitations", "rejected_alternatives"):
            result[key] = list(result[key])
        return result


def assess_rotation_inputs(
    *,
    region_code: str,
    crop_history: Iterable[Mapping[str, Any]],
    calendar: Mapping[str, Any] | None,
    crop_profiles: Iterable[Mapping[str, Any]],
    environmental_inputs: Iterable[Mapping[str, Any]] = (),
    priorities: Mapping[str, float] | None = None,
    documented_constraints: Iterable[Mapping[str, Any]] = (),
    candidate_rotations: Iterable[Mapping[str, Any]] = (),
    planning_seasons: int = 4,
) -> RotationAssessment:
    """Assess evidence readiness; never infer missing values or invent crops.

    Candidate sequence generation is intentionally gated on a sourced calendar
    and at least one eligible profile for every required season. Hard rules are
    enforced only when explicitly marked approved and evidence-linked.
    """
    history = list(crop_history)
    profiles = list(crop_profiles)
    environment = list(environmental_inputs)
    constraints = list(documented_constraints)
    missing: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    limitations = [
        "No yield, profit, market-price, or guaranteed soil-health outcomes are predicted.",
        "NASA POWER observations are gridded environmental estimates, not farm-level measurements.",
        "Environmental observations are retained for context only; they are not used for crop-suitability matching because no approved regional growth-period mapping and compatible sourced crop thresholds are configured.",
        "Options are not ranked; no objective comparison rubric or evidence-quality confidence method is approved.",
        "The engine checks approved regional calendar membership and evidence presence only; crop suitability and crop traits are NOT_EVALUATED because no approved trait-evaluation rule set is configured.",
        "The requested WATER_EFFICIENT and SOIL_REGENERATION preference strategies are not generated until reviewed preference criteria and traits exist.",
        "Farmer-selected priorities are preserved in the assessment input but do not influence option generation or ranking until an agronomically reviewed preference method is approved.",
    ]

    if not region_code:
        missing.append({"name": "region_code", "reason": "Farm region is not configured."})
    if calendar is None:
        missing.append({
            "name": "regional_crop_calendar",
            "reason": f"No approved, source-backed crop calendar is configured for {region_code or 'this farm'}.",
        })
    if not profiles:
        missing.append({
            "name": "eligible_crop_profiles",
            "reason": "No approved source-backed crop profiles are available for this region.",
        })
    if not history:
        missing.append({"name": "crop_history", "reason": "No farmer-reported crop history is available; baseline cannot be established."})
    else:
        unknown_codes = [item for item in history if not item.get("crop_code")]
        if unknown_codes:
            missing.append({
                "name": "crop_history_crop_codes",
                "reason": "Some history entries contain names only and cannot be safely matched to catalog crop identities.",
            })
        labels = [str(item.get("season", "")).strip().casefold() for item in history]
        sources = [str(item.get("source", "UNKNOWN")) for item in history]
        if len(set(sources)) > 1:
            missing.append({
                "name": "crop_history_provenance_conflict",
                "reason": "Crop-history records have different provenance labels; the baseline is lower-confidence and provenance differences are retained for review.",
            })
        if any(not label for label in labels):
            missing.append({
                "name": "crop_history_season_labels",
                "reason": "Some crop-history records have no season label, so chronological order cannot be verified.",
            })
        if len(labels) != len(set(labels)):
            missing.append({
                "name": "crop_history_conflicts",
                "reason": "Multiple history entries use the same season label; the sequence is ambiguous and requires farmer clarification.",
            })
        if len(history) < planning_seasons:
            missing.append({
                "name": "baseline_horizon",
                "reason": f"History has {len(history)} season(s), fewer than the requested {planning_seasons}-season horizon.",
            })

    if calendar is not None:
        seasons = calendar.get("seasons", [])
        if not seasons:
            missing.append({"name": "calendar_seasons", "reason": "The approved calendar has no season definitions."})
        else:
            for season in seasons:
                if not season.get("evidence_ids") or not all(str(value).strip() for value in season.get("evidence_ids", [])):
                    missing.append({
                        "name": f"calendar_evidence:{season.get('season_code', 'unknown')}",
                        "reason": "A calendar season has no traceable source evidence.",
                    })

    approved_rules = [
        rule for rule in constraints
        if rule.get("approved") is True and rule.get("evidence_id") and rule.get("source")
    ]
    for rule in constraints:
        if rule.get("approved") and (not rule.get("evidence_id") or not rule.get("source")):
            rejected.append({
                "constraint": str(rule.get("id", "unknown")),
                "reason": "Constraint was not applied because it lacks a traceable source and evidence reference.",
            })
    supported_rules = [rule for rule in approved_rules if rule.get("rule_type") == "FORBID_ADJACENT_CROP"]
    applied_constraints = [
        {key: value for key, value in rule.items() if key != "approved"}
        for rule in supported_rules
    ]
    for rule in approved_rules:
        if rule.get("rule_type") not in {"FORBID_ADJACENT_CROP"}:
            rejected.append({
                "constraint": str(rule.get("id", "unknown")),
                "reason": "Approved constraint type is not supported by this engine version; it was reported but not applied.",
            })

    if not environment:
        limitations.append("No usable NASA POWER observations are available; environmental compatibility was not assessed and no climate-based preference or exclusion was applied.")
    elif any(not item.get("source") or not item.get("parameter") or not item.get("unit") for item in environment):
        missing.append({
            "name": "environmental_provenance",
            "reason": "At least one environmental input lacks source, parameter, or unit provenance and was not used.",
        })
        environment = [item for item in environment if item.get("source") and item.get("parameter") and item.get("unit")]

    if priorities:
        unknown_priorities = set(priorities) - {"water_conservation", "soil_regeneration", "market_income", "forage_value"}
        if unknown_priorities:
            missing.append({"name": "priority_keys", "reason": f"Unsupported priorities: {', '.join(sorted(unknown_priorities))}."})

    profile_by_code = {str(profile.get("crop_code")): profile for profile in profiles}
    candidates = list(candidate_rotations)
    if calendar is not None and calendar.get("candidate_generation_limited"):
        limitations.append("Candidate combinations were deterministically capped at 100; this assessment is not an exhaustive enumeration.")
    options: list[dict[str, Any]] = []
    history_labels = [str(item.get("season", "")).strip().casefold() for item in history]
    history_conflicts = (
        len(history_labels) != len(set(history_labels))
        or any(not label for label in history_labels)
    )
    if len(history) >= planning_seasons and not history_conflicts and not any(
        not item.get("crop_code") for item in history[-planning_seasons:]
    ):
        baseline = history[-planning_seasons:]
        options.append({
            "option_id": "BASELINE",
            "strategy_type": "BASELINE",
            "seasons": [
                {"season_code": item.get("season"), "crop_code": item.get("crop_code"),
                 "crop_name": item.get("crop"), "source": item.get("source", "USER_PROVIDED"),
                 "history_id": item.get("history_id"), "start_date": None, "end_date": None,
                 "temporal_status": "UNDATED_HISTORY",
                 "regional_catalogue_match": item.get("regional_catalogue_match", "UNKNOWN")}
                for item in baseline
            ],
            "score": None,
            "confidence": {"status": "NOT_ASSESSED", "reason": "Farmer-entered history is not independently verified."},
            "why_suggested": "Historical comparison only: this option exactly reproduces the farmer-entered crops for the selected seasons; it is not a future agronomic recommendation.",
            "traits_evaluated": [],
            "trait_evaluation": {"status": "NOT_EVALUATED", "reason": "Historical entries are reported as recorded; crop suitability is not evaluated."},
            "constraints_satisfied": [],
            "constraints_not_evaluated": list(constraints),
            "evidence": [str(item.get("history_id")) for item in baseline if item.get("history_id")],
            "data_gaps": ["Historical entries are farmer-reported and do not establish future suitability."] + [item["reason"] for item in missing],
            "environmental_inputs_considered": [dict(item) for item in environment],
            "farmer_priorities_considered": dict(priorities or {}),
            "assumptions": [],
        })
    for candidate in candidates:
        seasons = list(candidate.get("seasons", []))
        if len(seasons) != planning_seasons:
            rejected.append({"candidate": str(candidate.get("id", "unknown")), "reason": "Candidate does not cover the requested planning horizon."})
            continue
        candidate_missing = []
        for season in seasons:
            profile = profile_by_code.get(str(season.get("crop_code", "")))
            if profile is None:
                candidate_missing.append(f"No eligible source-backed profile for {season.get('crop_code', 'unknown crop')}.")
            elif profile.get("conflicting_traits"):
                candidate_missing.append(
                    f"Conflicting source values require review for traits: {', '.join(profile['conflicting_traits'])}."
                )
            elif profile is not None:
                available_traits = {trait.get("trait") for trait in profile.get("characteristics", [])}
                for required_trait in candidate.get("required_traits", []):
                    if required_trait not in available_traits:
                        candidate_missing.append(f"Required trait {required_trait} is unknown for crop {profile.get('crop_code')}.")
            if not season.get("evidence_ids") or not all(str(value).strip() for value in season.get("evidence_ids", [])):
                candidate_missing.append(f"No source evidence for season {season.get('season_code', 'unknown')}.")
            if not season.get("start_date") or not season.get("end_date"):
                candidate_missing.append(f"Season dates are incomplete for {season.get('season_code', 'unknown')}.")
            if profile is not None:
                allowed_codes = set(season.get("allowed_crop_codes", []))
                if allowed_codes and season.get("crop_code") not in allowed_codes:
                    candidate_missing.append(f"Crop {season.get('crop_code')} is not listed for season {season.get('season_code')} in the approved calendar.")
        if candidate_missing:
            rejected.append({"candidate": str(candidate.get("id", "unknown")), "reason": " ".join(candidate_missing)})
            continue
        excluded = False
        crop_codes = [str(season["crop_code"]) for season in seasons]
        for rule in supported_rules:
            if rule.get("rule_type") == "FORBID_ADJACENT_CROP" and rule.get("crop_code") in crop_codes:
                if any(left == right == rule["crop_code"] for left, right in zip(crop_codes, crop_codes[1:])):
                    rejected.append({"candidate": str(candidate.get("id", "unknown")), "reason": f"Excluded by documented rule {rule.get('id')}: {rule.get('description', 'incompatible adjacent sequence')} (evidence {rule['evidence_id']})."})
                    excluded = True
                    break
            elif rule.get("rule_type") != "FORBID_ADJACENT_CROP":
                rejected.append({"constraint": str(rule.get("id", "unknown")), "reason": "Approved constraint type is not implemented; it was not used to exclude a candidate."})
        if excluded:
            continue
        options.append({
            "option_id": str(candidate.get("id", "candidate")),
            "seasons": seasons,
            "score": None,
            "confidence": {"status": "NOT_ASSESSED", "reason": "No approved evidence-quality rubric."},
            "why_suggested": str(candidate.get("explanation", "Listed in the approved regional calendar and passed the implemented evidence and documented-rule checks; this does not establish crop suitability or an objectively best rotation.")),
            "traits_evaluated": [],
            "trait_evaluation": {
                "status": "NOT_EVALUATED",
                "reason": "This sequence is calendar-eligible only; no crop trait values or suitability thresholds were evaluated.",
            },
            "constraints_satisfied": list(applied_constraints),
            "constraints_not_evaluated": [item for item in constraints if item not in supported_rules],
            "history_considered": history[-planning_seasons:],
            "farmer_priorities_considered": dict(priorities or {}),
            "evidence": sorted({str(evidence_id) for season in seasons for evidence_id in season.get("evidence_ids", [])}),
            "data_gaps": list(candidate.get("data_gaps", [])) + [item["reason"] for item in missing],
            "assumptions": list(candidate.get("assumptions", [])),
        })

    blocking_missing = [
        item for item in missing
        if item["name"] not in {
            "priority_keys", "environmental_provenance", "crop_history_season_labels",
            "crop_history_order", "crop_history", "crop_history_crop_codes",
            "baseline_horizon", "crop_history_conflicts", "crop_history_provenance_conflict",
        }
    ]
    ready = bool(options) and not blocking_missing
    if not ready:
        # The status is authoritative: diagnostic candidates must never leak into
        # the recommendation list when a hard evidence gate failed.
        options = []
    if not candidates and not options:
        missing.append({"name": "candidate_sequences", "reason": "No candidate sequences are configured from approved calendar and rotation-rule evidence."})
    if not ready:
        limitations.append("No rotation is recommended because essential regional calendar, history, crop-profile, candidate-sequence, or environmental-period evidence is missing or ambiguous.")
    return RotationAssessment(
        status="OPTIONS_AVAILABLE" if ready else "INSUFFICIENT_EVIDENCE",
        options=tuple(options),
        missing=tuple(_deduplicate(missing)),
        constraints=tuple(applied_constraints),
        environmental_inputs=tuple(
            {**item, "used_for_suitability": False}
            for item in environment
        ),
        data_limitations=tuple(limitations),
        rejected_alternatives=tuple(rejected),
    )


def _deduplicate(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for item in items:
        key = (item["name"], item["reason"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

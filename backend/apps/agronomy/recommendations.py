"""Reproducible recommendation snapshots and their owner-scoped API services."""

from __future__ import annotations

import hashlib
import itertools
import json
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.agronomy.models import AgriculturalDataset, CropAlias, CropCharacteristic, CropRotationRule, GeographicApplicability, RegionAgronomyProfile, RotationRecommendation, ValidationStatus
from apps.earth_data.models import EnvironmentalObservation
from apps.farms.models import FarmCropHistory, FarmerContext

from .rotation import ENGINE_VERSION, assess_rotation_inputs

def generate_recommendation(*, farm, requested_by, planning_seasons: int, region_code: str | None = None, priorities: dict | None = None, planning_start_date: date | None = None):
    """Build and persist a source-auditable assessment for one owned farm."""
    effective_region = farm.region_code
    context = FarmerContext.objects.filter(farm=farm).first()
    if priorities is None and context is not None:
        priorities = context.priorities or None
    history_qs = FarmCropHistory.objects.filter(context__farm=farm).order_by("sequence", "id")
    history_rows = list(history_qs)
    history = [_history_entry(row, effective_region) for row in history_rows]
    if len({(row.sequence, row.id) for row in history_rows}) != len(history_rows):
        history.append({"season": "", "crop": "", "crop_code": None, "source": "UNKNOWN", "conflict": True})
    profiles = _eligible_profiles(effective_region)
    environment = _environment_snapshot(farm)
    planning_start_date = planning_start_date or date.today()
    calendar, candidate_rotations = _calendar_candidates(effective_region, planning_seasons, planning_start_date)
    rules = _documented_rules(effective_region)
    assessment = assess_rotation_inputs(
        region_code=effective_region,
        crop_history=history,
        calendar=calendar,
        crop_profiles=profiles,
        environmental_inputs=environment,
        priorities=priorities,
        documented_constraints=rules,
        candidate_rotations=candidate_rotations,
        planning_seasons=planning_seasons,
    )
    assessment_data = assessment.as_dict()
    if region_code and region_code.casefold() != effective_region.casefold():
        assessment_data["status"] = "INSUFFICIENT_EVIDENCE"
        assessment_data["options"] = []
        assessment_data["missing"].append({"name": "region_code_mismatch", "reason": "Requested region must match the farm's configured region."})

    inputs = {
        "farm_id": farm.pk,
        "region_code": effective_region,
        "farm_geometry": json.loads(farm.boundary.geojson) if farm.boundary else None,
        "farm_location": json.loads(farm.location.geojson) if farm.location else None,
        "calendar": calendar,
        "documented_constraints": rules,
        "candidate_rotations": candidate_rotations,
        "rotation_rules": rules,
        "crop_history": history,
        "crop_profiles": profiles,
        "environmental_digest": environment,
        "priorities": priorities or {},
        "farmer_context": {
            "soil_source": context.soil_source if context else None,
            "texture_class": context.texture_class if context else None,
            "ph": str(context.ph) if context and context.ph is not None else None,
            "organic_carbon_percent": str(context.organic_carbon_percent) if context and context.organic_carbon_percent is not None else None,
            "nitrogen_ppm": str(context.nitrogen_ppm) if context and context.nitrogen_ppm is not None else None,
            "phosphorus_ppm": str(context.phosphorus_ppm) if context and context.phosphorus_ppm is not None else None,
            "potassium_ppm": str(context.potassium_ppm) if context and context.potassium_ppm is not None else None,
            "sampling_depth_cm": context.sampling_depth_cm if context else None,
            "sampling_method": context.sampling_method if context else None,
            "sample_date": context.sample_date.isoformat() if context and context.sample_date else None,
            "constraints": context.constraints if context else None,
            "water_source": context.water_source if context else None,
            "irrigation_available": context.irrigation_available if context else None,
        },
        "planning_seasons": planning_seasons,
        "planning_start_date": planning_start_date.isoformat(),
    }
    # Hash only decision inputs; observation age is response metadata and must not
    # make an otherwise identical recalculation nondeterministic from day to day.
    hash_inputs = inputs
    canonical = json.dumps(hash_inputs, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    with transaction.atomic():
        result = RotationRecommendation.objects.create(
            farm=farm,
            requested_by=requested_by,
            engine_version=ENGINE_VERSION,
            input_snapshot=inputs,
            input_sha256=digest,
            assessment=assessment_data,
            status=assessment_data["status"],
        )
    return result


def _history_entry(row, region_code: str) -> dict[str, Any]:
    """Preserve farmer text and only link a reviewed, unambiguous region alias."""
    alias = row.crop_code or row.crop_name
    mappings = list(CropAlias.objects.filter(region_code__iexact=region_code, alias__iexact=alias, is_active=True).select_related("canonical_crop")) if region_code and alias else []
    canonical = mappings[0].canonical_crop if len(mappings) == 1 else None
    return {
        "season": row.season_label,
        "crop": row.crop_name,
        "crop_code": canonical.code if canonical else None,
        "reported_crop_code": row.crop_code or None,
        "canonical_crop_id": canonical.pk if canonical else None,
        "regional_catalogue_match": "MATCHED" if canonical else "AMBIGUOUS" if len(mappings) > 1 else "UNRESOLVED",
        "source": row.source,
        "notes": row.notes,
        "history_id": row.pk,
    }


def _calendar_candidates(region_code: str, planning_seasons: int, planning_start_date: date) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    profile = RegionAgronomyProfile.objects.filter(
        region_code__iexact=region_code,
        status=AgriculturalDataset.Status.APPROVED,
    ).prefetch_related("seasons__crop_windows__crop").order_by("-calendar_version").first()
    if profile is None:
        return None, []
    seasons = list(profile.seasons.all())
    calendar = {
        "region_code": profile.region_code,
        "calendar_version": profile.calendar_version,
        "seasons": [
            {"season_code": season.season_code, "label": season.label,
             "start_month_day": season.start_month_day, "end_month_day": season.end_month_day,
             "evidence_ids": [season.evidence_reference], "source_url": season.source_url,
             "crop_codes": [window.crop.code for window in season.crop_windows.all()]}
            for season in seasons
        ],
    }
    if not seasons:
        return calendar, []
    slots = []
    cycle_start = profile.season_cycle_start_month_day
    if not cycle_start:
        calendar["cycle_anchor_missing"] = True
        return calendar, []
    occurrences = []
    try:
        for year in range(planning_start_date.year - 1, planning_start_date.year + planning_seasons + 2):
            for season in seasons:
                start_year = year + (1 if season.start_month_day < cycle_start else 0)
                start_date = date.fromisoformat(f"{start_year}-{season.start_month_day}")
                end_year = start_year + (1 if season.end_month_day < season.start_month_day else 0)
                end_date = date.fromisoformat(f"{end_year}-{season.end_month_day}")
                if start_date >= planning_start_date:
                    occurrences.append((season, start_date, end_date))
    except ValueError:
        return calendar, []
    occurrences.sort(key=lambda item: (item[1], item[0].sequence, item[0].season_code))
    slots = []
    for season, start_date, end_date in occurrences[:planning_seasons]:
        crops = list(season.crop_windows.all())
        slots.append((season, start_date, end_date, crops))
    if len(slots) != planning_seasons:
        return calendar, []
    choices = [slot[3] for slot in slots]
    if any(not choice for choice in choices):
        return calendar, []
    candidates = []
    combinations = itertools.product(*choices)
    for number, combination in enumerate(itertools.islice(combinations, 101), start=1):
        candidates.append({
            "id": f"{profile.calendar_version}:{number}",
            "seasons": [
                {"season_code": slot[0].season_code,
                 "allowed_crop_codes": [choice.crop.code for choice in slot[3]],
                 "start_date": slot[1].isoformat(), "end_date": slot[2].isoformat(),
                 "crop_code": crop.crop.code,
                 "evidence_ids": [slot[0].evidence_reference, crop.evidence_reference],
                 "required_traits": [],
                 "planting_window": crop.planting_window or None,
                 "harvest_window": crop.harvest_window or None}
                for slot, crop in zip(slots, combination)
            ],
        })
    if number > 100:
        candidates = candidates[:100]
        calendar["candidate_generation_limited"] = True
    return calendar, candidates


def _documented_rules(region_code: str) -> list[dict[str, Any]]:
    rules = CropRotationRule.objects.filter(
        profile__region_code__iexact=region_code,
        profile__status=AgriculturalDataset.Status.APPROVED,
        approved=True,
    ).select_related("crop", "profile").order_by("identifier")
    return [{
        "id": rule.identifier,
        "approved": rule.approved,
        "source": rule.source_title,
        "evidence_id": rule.evidence_reference,
        "rule_type": rule.rule_type,
        "crop_code": rule.crop.code,
        "description": rule.description,
        "source_url": rule.source_url,
        "calendar_version": rule.profile.calendar_version,
    } for rule in rules]


def _eligible_profiles(region_code: str) -> list[dict[str, Any]]:
    """Return only approved imports and validated, region-eligible traits."""
    if not region_code:
        return []
    rows = CropCharacteristic.objects.filter(
        dataset__status=AgriculturalDataset.Status.APPROVED,
        dataset_import__status="SUCCEEDED",
        approval_status="APPROVED",
        validation_status=ValidationStatus.VALID,
    ).exclude(
        Q(original_value__isnull=True) | Q(original_value="")
    ).filter(
        (Q(approved_geographic_applicability__in=(GeographicApplicability.GENERAL, GeographicApplicability.TRANSFERABLE_LIMITED)))
        | Q(approved_geographic_applicability=GeographicApplicability.DIRECT, geographic_scope__iexact=region_code)
    ).select_related("crop", "dataset").order_by("crop__code", "characteristic_name", "id").distinct()
    profiles: dict[str, dict[str, Any]] = {}
    for trait in rows:
        if trait.approved_geographic_applicability == GeographicApplicability.DIRECT and trait.geographic_scope.casefold() != region_code.casefold():
            continue
        crop = profiles.setdefault(trait.crop.code, {
            "crop_code": trait.crop.code,
            "name": trait.crop.name,
            "crop_family": trait.crop.crop_family or None,
            "characteristics": [],
        })
        crop["characteristics"].append({
            "trait": trait.characteristic_name,
            "value": trait.original_value,
            "unit": trait.original_unit or None,
            "normalized_value": (
                str(trait.normalized_value) if trait.normalized_value is not None
                else trait.normalized_text if trait.normalized_text is not None
                else trait.normalized_boolean
            ),
            "normalized_unit": trait.normalized_unit or None,
            "source": trait.original_dataset_identifier,
            "publisher": trait.original_publisher,
            "dataset_version": trait.original_dataset_version or None,
            "license": trait.source_license or None,
            "attribution": trait.source_attribution or None,
            "landing_page_url": trait.original_dataset_landing_page_url or None,
            "resource_identifier": trait.source_resource_identifier or None,
            "resource_url": trait.source_resource_url or None,
            "source_record_identifier": trait.source_record_identifier,
            "source_record_url": trait.source_record_url or None,
            "evidence_reference": trait.evidence_reference or None,
            "geographic_applicability": trait.geographic_applicability,
            "geographic_scope": trait.geographic_scope or None,
            "temporal_applicability": trait.temporal_applicability or None,
            "validation_status": trait.validation_status,
        })
    for profile in profiles.values():
        values_by_trait: dict[str, set[tuple[str | None, str | None]]] = {}
        for trait in profile["characteristics"]:
            values_by_trait.setdefault(trait["trait"], set()).add((trait["normalized_value"], trait["normalized_unit"]))
        profile["conflicting_traits"] = sorted(
            name for name, values in values_by_trait.items()
            if len(values) > 1 and any(value is not None for value, _ in values)
        )
    return list(profiles.values())


def _environment_snapshot(farm) -> list[dict[str, Any]]:
    """Snapshot recent stored POWER rows with actual date, units and provenance."""
    latest = EnvironmentalObservation.objects.filter(
        farm=farm,
        quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
        source__is_active=True,
    ).order_by("-observation_date").values_list("observation_date", flat=True).first()
    if latest is None:
        return []
    cutoff = latest - timedelta(days=365)
    today = timezone.localdate()
    observations = EnvironmentalObservation.objects.filter(
        farm=farm,
        observation_date__gte=cutoff,
        quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
        source__is_active=True,
    ).select_related("source").order_by("observation_date", "source__parameter_code")
    return [
        {
            "date": row.observation_date.isoformat(),
            "temporal_coverage": {"start": row.observation_date.isoformat(), "end": row.observation_date.isoformat()},
            "value": str(row.value),
            "parameter": row.source.parameter_code,
            "unit": row.source.units,
            "source": row.source.provider,
            "product": row.source.product,
            "data_category": row.source.data_category,
            "native_resolution_note": row.source.native_resolution_note or None,
            "quality": row.quality_status,
            "age_days": (today - row.observation_date).days,
            "freshness": "FRESH" if (today - row.observation_date).days <= 7 else "RECENT" if (today - row.observation_date).days <= 30 else "STALE",
            "fetch_job_id": str(row.fetch_job_id) if row.fetch_job_id else None,
        }
        for row in observations
    ]


def recommendation_payload(result: RotationRecommendation) -> dict[str, Any]:
    return {
        "recommendation_id": str(result.pk),
        "farm_id": result.farm_id,
        "generated_at": result.generated_at.isoformat().replace("+00:00", "Z"),
        "engine_version": result.engine_version,
        "status": result.status,
        "planning_horizon": {"season_count": result.input_snapshot["planning_seasons"], "start_date": result.input_snapshot["planning_start_date"], "calendar_version": result.input_snapshot["calendar"].get("calendar_version") if result.input_snapshot.get("calendar") else None},
        "data_completeness": {"status": "NOT_ASSESSED", "value": None, "reason": "No approved completeness method."},
        "input_sha256": result.input_sha256,
        "options": result.assessment["options"],
        "missing": result.assessment["missing"],
        "constraints": result.assessment["constraints"],
        "methodology": {"id": "rotation.evidence-gated.v1", "version": result.engine_version},
        "rejected_alternatives": result.assessment["rejected_alternatives"],
        "environmental_digest": result.assessment["environmental_inputs"],
        "crop_profiles": result.input_snapshot["crop_profiles"],
        "farm_geometry": result.input_snapshot["farm_geometry"],
        "farm_location": result.input_snapshot["farm_location"],
        "farmer_context": result.input_snapshot["farmer_context"],
        "data_limitations": result.assessment["data_limitations"],
        "explanation": {
            "why_presented": "This assessment records what the available evidence can and cannot support; it does not claim an objectively best rotation.",
            "methodology": "Deterministic evidence-readiness gate; no arbitrary score or unsupported threshold.",
        },
    }

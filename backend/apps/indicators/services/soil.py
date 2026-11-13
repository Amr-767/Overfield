"""Soil indicator calculations (Phase 4C).

Approved methodology (R17 / ADR-023):

* every available property is reported **independently** — no composite
  soil-health score and no 0–100 number;
* pH uses descriptive bands only (ACIDIC < 6.0, NEUTRAL 6.0–7.5, ALKALINE > 7.5);
* organic carbon is reported as measured, with no universal good/bad threshold
  and no trend inferred from a single sample;
* N/P/K are reported in ppm with the sampling method preserved; they are never
  classified as deficient/sufficient/excessive, and results from different
  extraction methods are not treated as interchangeable;
* texture is qualitative context only — no water-holding capacity is derived;
* sample age uses operational labels (FRESH < 12 months, AGEING 12–24,
  STALE > 24) and is reported separately from confidence.

Nothing here infers laboratory values from weather data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from django.conf import settings

from ..contract import (
    Completeness,
    Confidence,
    Driver,
    DriverDirection,
    Freshness,
    IndicatorResult,
    IndicatorStatus,
    Measurement,
    Methodology,
    MissingInput,
    Period,
)
from ..coverage import confidence_for

SOIL_METHODOLOGY = Methodology(
    id="soil.properties.v1",
    version="1.0.0",
    description=(
        "Per-property soil reporting from the farmer context: pH, organic carbon, N/P/K, "
        "texture, sampling metadata and sample age. No composite soil-health score."
    ),
    threshold_source=(
        "pH bands are descriptive (ACIDIC < 6.0, NEUTRAL 6.0-7.5, ALKALINE > 7.5). "
        "Sample-age labels are operational (INDICATOR_SOIL_FRESH_MONTHS=12, "
        "INDICATOR_SOIL_STALE_MONTHS=24). No crop-suitability or nutrient thresholds."
    ),
)

ACIDIC = "ACIDIC"
NEUTRAL = "NEUTRAL"
ALKALINE = "ALKALINE"

#: Core properties used for completeness and status.
CORE_PROPERTIES: tuple[str, ...] = (
    "ph",
    "organic_carbon_percent",
    "nitrogen_ppm",
    "phosphorus_ppm",
    "potassium_ppm",
    "texture_class",
)

PROVENANCE_FACTORS: Mapping[str, Decimal] = {
    "LAB_TEST": Decimal("1.00"),
    "EXTERNAL_PROVIDER": Decimal("0.80"),
    "FARMER_REPORTED": Decimal("0.70"),
    "REMOTE_SENSING": Decimal("0.60"),
    "UNKNOWN": Decimal("0.40"),
}

FRESHNESS_FACTORS: Mapping[Freshness, Decimal] = {
    Freshness.FRESH: Decimal("1.00"),
    Freshness.AGEING: Decimal("0.75"),
    Freshness.STALE: Decimal("0.50"),
    Freshness.UNKNOWN: Decimal("0.60"),
    Freshness.FUTURE: Decimal("0.40"),
    Freshness.RECENT: Decimal("0.75"),
}


@dataclass(frozen=True, slots=True)
class SoilProfile:
    """Farmer-context soil fields, decoupled from the ORM for pure calculation."""

    soil_source: str = "UNKNOWN"
    texture_class: str = ""
    ph: Decimal | None = None
    organic_carbon_percent: Decimal | None = None
    nitrogen_ppm: Decimal | None = None
    phosphorus_ppm: Decimal | None = None
    potassium_ppm: Decimal | None = None
    sampling_depth_cm: int | None = None
    sampling_method: str = ""
    lab_name: str = ""
    sample_date: date | None = None


def ph_band(value: Decimal | None) -> str | None:
    """Descriptive pH band only — never a crop-suitability verdict."""
    if value is None:
        return None
    if value < Decimal("6.0"):
        return ACIDIC
    if value <= Decimal("7.5"):
        return NEUTRAL
    return ALKALINE


def _subtract_months(value: date, months: int) -> date:
    """Calendar-month subtraction, clamping month-end (e.g. Mar 31 -> Feb 28)."""
    month_index = value.year * 12 + (value.month - 1) - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    # Import locally to keep the common indicator module light.
    import calendar

    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def sample_freshness(sample_date: date | None, today: date) -> Freshness:
    """Operational sample-age label; future dates are flagged, never 'fresh'."""
    if sample_date is None:
        return Freshness.UNKNOWN
    if sample_date > today:
        return Freshness.FUTURE

    fresh_months = int(getattr(settings, "INDICATOR_SOIL_FRESH_MONTHS", 12))
    stale_months = int(getattr(settings, "INDICATOR_SOIL_STALE_MONTHS", 24))
    fresh_cutoff = _subtract_months(today, fresh_months)
    stale_cutoff = _subtract_months(today, stale_months)
    # Exact anniversary belongs to the older band: <12 months is FRESH;
    # 12 months through 24 months (inclusive) is AGEING; >24 months is STALE.
    if sample_date > fresh_cutoff:
        return Freshness.FRESH
    if sample_date >= stale_cutoff:
        return Freshness.AGEING
    return Freshness.STALE


def _confidence(
    *,
    completeness_ratio: Decimal,
    provenance: str,
    freshness: Freshness,
) -> Confidence:
    """Completeness × provenance × sample age, mapped to the shared bands."""
    provenance_factor = PROVENANCE_FACTORS.get(provenance, PROVENANCE_FACTORS["UNKNOWN"])
    freshness_factor = FRESHNESS_FACTORS.get(freshness, Decimal("0.5"))
    score = (completeness_ratio * provenance_factor * freshness_factor).quantize(Decimal("0.0001"))
    return confidence_for(score)


def calculate_soil_indicator(
    *,
    profile: SoilProfile | None,
    today: date,
) -> IndicatorResult:
    """Build the SOIL indicator from a farmer-context soil profile."""
    if profile is None:
        return _empty_result(today=today, reason="no farmer context")

    present = [name for name in CORE_PROPERTIES if _has_value(profile, name)]
    completeness = Completeness(
        properties_expected=len(CORE_PROPERTIES), properties_present=len(present)
    )
    freshness = sample_freshness(profile.sample_date, today)
    period = (
        Period(
            start=profile.sample_date,
            end=profile.sample_date,
            latest_observation=profile.sample_date,
            age_days=(today - profile.sample_date).days,
            freshness=freshness,
        )
        if profile.sample_date is not None
        else None
    )

    if not present:
        return _empty_result(today=today, reason="no soil properties recorded", period=period)

    status = (
        IndicatorStatus.OK
        if len(present) == len(CORE_PROPERTIES)
        else IndicatorStatus.PARTIAL
    )
    confidence = _confidence(
        completeness_ratio=completeness.ratio,
        provenance=profile.soil_source,
        freshness=freshness,
    )

    measurements = _measurements(profile)
    context = _context(profile)
    missing = _missing_inputs(profile, present)

    limitations = [
        "No composite soil-health score is produced; each property is reported on its own.",
        "N/P/K values depend on the laboratory extraction method and are not comparable across methods.",
        "A single sample cannot show a trend; repeat sampling is required.",
        "Texture is qualitative context only; no water-holding capacity is derived from it.",
        "pH bands are descriptive, not a crop-suitability judgement.",
        "Sample-age labels are operational data-freshness flags, not validity guarantees.",
    ]
    if freshness is Freshness.FUTURE:
        limitations.append(
            "The recorded sample date is in the future; freshness is flagged as FUTURE and not treated as fresh."
        )
    if freshness is Freshness.UNKNOWN:
        limitations.append("No sample date is recorded, so sample age cannot be determined.")

    return IndicatorResult(
        code="SOIL",
        label="Soil",
        status=status,
        confidence=confidence,
        period=period,
        coverage=None,
        completeness=completeness,
        summary=_summary(profile, present, freshness),
        measurements=measurements,
        context=context,
        drivers=(
            Driver(
                name="Soil properties recorded",
                direction=DriverDirection.NEUTRAL,
                value=f"{len(present)}/{len(CORE_PROPERTIES)}",
            ),
            Driver(
                name="Sample freshness",
                direction=DriverDirection.NEUTRAL,
                value=freshness.value,
            ),
        ),
        missing=missing,
        methodology=SOIL_METHODOLOGY,
        sources=(),
        limitations=tuple(limitations),
    )


def _has_value(profile: SoilProfile, name: str) -> bool:
    value = getattr(profile, name)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _measurements(profile: SoilProfile) -> tuple[Measurement, ...]:
    method = profile.sampling_method or "not recorded"
    provenance = profile.soil_source
    items: list[Measurement] = []

    if profile.ph is not None:
        items.append(
            Measurement(
                name="ph",
                value=profile.ph,
                unit="pH",
                source=provenance,
                quality=provenance,
                method=method,
                interpretation=ph_band(profile.ph),
            )
        )
    if profile.organic_carbon_percent is not None:
        items.append(
            Measurement(
                name="organic_carbon_percent",
                value=profile.organic_carbon_percent,
                unit="%",
                source=provenance,
                quality=provenance,
                method=method,
                interpretation=None,
            )
        )
    for name, label in (
        ("nitrogen_ppm", "nitrogen"),
        ("phosphorus_ppm", "phosphorus"),
        ("potassium_ppm", "potassium"),
    ):
        value = getattr(profile, name)
        if value is not None:
            items.append(
                Measurement(
                    name=name,
                    value=value,
                    unit="ppm",
                    source=provenance,
                    quality=provenance,
                    method=method,
                    interpretation=None,
                )
            )
    if profile.texture_class:
        items.append(
            Measurement(
                name="texture_class",
                value=profile.texture_class,
                unit="class",
                source=provenance,
                quality=provenance,
                method=method,
                interpretation="qualitative texture class; no water-holding capacity inferred",
            )
        )
    return tuple(items)


def _context(profile: SoilProfile) -> tuple[Measurement, ...]:
    items: list[Measurement] = []
    if profile.sample_date is not None:
        items.append(
            Measurement(
                name="sample_date",
                value=profile.sample_date.isoformat(),
                unit="date",
                source=profile.soil_source,
                quality=profile.soil_source,
                method="recorded sample date",
            )
        )
    if profile.sampling_depth_cm is not None:
        items.append(
            Measurement(
                name="sampling_depth_cm",
                value=profile.sampling_depth_cm,
                unit="cm",
                source=profile.soil_source,
                quality=profile.soil_source,
                method="recorded sampling depth",
            )
        )
    if profile.sampling_method:
        items.append(
            Measurement(
                name="sampling_method",
                value=profile.sampling_method,
                unit="text",
                source=profile.soil_source,
                quality=profile.soil_source,
                method="recorded extraction/sampling method",
            )
        )
    if profile.lab_name:
        items.append(
            Measurement(
                name="lab_name",
                value=profile.lab_name,
                unit="text",
                source=profile.soil_source,
                quality=profile.soil_source,
                method="recorded laboratory",
            )
        )
    return tuple(items)


def _missing_inputs(profile: SoilProfile, present: list[str]) -> tuple[MissingInput, ...]:
    missing: list[MissingInput] = []
    for name in CORE_PROPERTIES:
        if name not in present:
            missing.append(
                MissingInput(
                    name=name,
                    impact="Not recorded; this property cannot be reported.",
                    required_for="soil condition",
                )
            )
    if profile.sample_date is None:
        missing.append(
            MissingInput(
                name="sample_date",
                impact="Sample age cannot be determined; freshness is UNKNOWN.",
                required_for="sample freshness",
            )
        )
    if not profile.sampling_method:
        missing.append(
            MissingInput(
                name="sampling_method",
                impact="N/P/K values cannot be compared with other laboratories.",
                required_for="nutrient comparability",
            )
        )
    return tuple(missing)


def _empty_result(
    *,
    today: date,
    reason: str,
    period: Period | None = None,
) -> IndicatorResult:
    return IndicatorResult(
        code="SOIL",
        label="Soil",
        status=IndicatorStatus.INSUFFICIENT_DATA,
        confidence=Confidence.NONE,
        # No sample date means there is no soil observation period.
        period=period,
        coverage=None,
        completeness=Completeness(
            properties_expected=len(CORE_PROPERTIES), properties_present=0
        ),
        summary=(
            "No soil information is recorded for this farm, so soil condition cannot be "
            "assessed. Add soil properties in the farm information form."
        ),
        missing=(
            MissingInput(
                name="farmer_context",
                impact=f"Soil properties are unavailable ({reason}).",
                required_for="soil condition",
            ),
            *(
                MissingInput(
                    name=name,
                    impact="Not recorded; this property cannot be reported.",
                    required_for="soil condition",
                )
                for name in CORE_PROPERTIES
            ),
        ),
        methodology=SOIL_METHODOLOGY,
        limitations=(
            "No soil measurement exists; nothing is inferred from weather data.",
            "No composite soil-health score is produced.",
        ),
    )


def _summary(profile: SoilProfile, present: list[str], freshness: Freshness) -> str:
    parts = [f"{len(present)} of {len(CORE_PROPERTIES)} soil properties recorded"]
    if profile.soil_source:
        parts.append(f"source {profile.soil_source}")
    if profile.sample_date:
        parts.append(f"sample dated {profile.sample_date.isoformat()} ({freshness.value})")
    else:
        parts.append("sample date not recorded")

    details: list[str] = []
    if profile.ph is not None:
        details.append(f"pH {profile.ph} ({ph_band(profile.ph)})")
    if profile.texture_class:
        details.append(f"texture {profile.texture_class}")
    if details:
        parts.append(", ".join(details))

    return "; ".join(parts) + ". No soil-health score is produced."


__all__ = [
    "ACIDIC",
    "ALKALINE",
    "CORE_PROPERTIES",
    "NEUTRAL",
    "SOIL_METHODOLOGY",
    "SoilProfile",
    "calculate_soil_indicator",
    "ph_band",
    "sample_freshness",
]

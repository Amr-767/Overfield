"""Water indicator calculations (Phase 4B).

Approved methodology (R15):

* the analysed window ends at the **latest available observation**;
* a rainy day is ``PRECTOTCORR >= 1.0 mm`` (configurable);
* totals are computed **only over covered days** and never presented as a
  complete-window total;
* a dry spell is only reported as contiguous when the window has no missing
  days; otherwise the longest *observed* run is reported with the limitation.

Nothing here claims soil moisture, plant-available water, irrigation demand,
ET deficit or water stress — those inputs do not exist in the project.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from django.conf import settings

from ..contract import (
    Confidence,
    Coverage,
    Driver,
    DriverDirection,
    IndicatorResult,
    IndicatorStatus,
    Measurement,
    Methodology,
    MissingInput,
    Period,
    SourceReference,
)
from ..coverage import (
    GRID_CELL_CONFIDENCE_CAP,
    as_decimal,
    build_period,
    confidence_for,
    count_days,
    coverage_from_values,
    days_in_window,
)

PARAMETER_CODE = "PRECTOTCORR"
UNIT_MM = "mm"

WATER_METHODOLOGY = Methodology(
    id="water.rainfall.v1",
    version="1.0.0",
    description=(
        "Rainfall summary over the latest available observation window: total, rainy "
        "days, maximum daily rainfall and longest observed dry run. No soil-moisture, "
        "evapotranspiration or irrigation modelling."
    ),
    threshold_source=(
        "Rainy-day threshold defaults to 1.0 mm/day (configurable via "
        "INDICATOR_RAINY_DAY_MM). No crop or regional threshold is assumed."
    ),
)

CONTIGUOUS = "CONTIGUOUS"
INTERRUPTED = "INTERRUPTED_BY_MISSING_DAYS"
UNKNOWN_CONTIGUITY = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DrySpell:
    """Longest observed run of days below the rainy-day threshold."""

    days: int | None
    contiguity: str


def default_rainy_day_threshold_mm() -> Decimal:
    return as_decimal(getattr(settings, "INDICATOR_RAINY_DAY_MM", None), "1.0")


def _longest_dry_run(
    days: Sequence[date],
    values: Mapping[date, Decimal | None],
    threshold: Decimal,
) -> DrySpell:
    if not any(values.get(day) is not None for day in days):
        return DrySpell(days=None, contiguity=UNKNOWN_CONTIGUITY)

    longest = 0
    current = 0
    saw_gap = False
    for day in days:
        value = values.get(day)
        if value is None:
            saw_gap = True
            current = 0
        elif value < threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return DrySpell(days=longest, contiguity=INTERRUPTED if saw_gap else CONTIGUOUS)


def calculate_water_indicator(
    *,
    precipitations: Mapping[date, Decimal | None],
    start: date,
    end: date,
    today: date,
    rainy_day_threshold_mm: Decimal | None = None,
    source: SourceReference | None = None,
    irrigation_context: Sequence[Measurement] = (),
) -> IndicatorResult:
    """Build the WATER indicator from daily precipitation values.

    ``precipitations`` maps every date to a value or ``None`` (not published).
    Dates absent from the mapping are treated as missing, never as zero.
    """
    threshold = rainy_day_threshold_mm or default_rainy_day_threshold_mm()
    days = days_in_window(start, end)
    values: dict[date, Decimal | None] = {day: precipitations.get(day) for day in days}

    coverage: Coverage = coverage_from_values(
        start, end, values, parameter=PARAMETER_CODE
    )
    covered_values = [value for value in values.values() if value is not None]
    total = sum(covered_values, Decimal("0")) if covered_values else None
    rainy_days = (
        sum(1 for value in covered_values if value >= threshold) if covered_values else None
    )
    max_daily = max(covered_values) if covered_values else None
    dry_spell = _longest_dry_run(days, values, threshold)

    latest_observation = max(
        (day for day, value in values.items() if value is not None), default=None
    )
    period: Period = build_period(
        start=start, end=end, latest_observation=latest_observation, today=today
    )

    if coverage.days_covered == 0:
        status = IndicatorStatus.INSUFFICIENT_DATA
    elif coverage.days_missing > 0:
        status = IndicatorStatus.PARTIAL
    else:
        status = IndicatorStatus.OK

    confidence = confidence_for(coverage.ratio, cap=GRID_CELL_CONFIDENCE_CAP)

    measurements = (
        Measurement(
            name="precipitation_total",
            value=total,
            unit=UNIT_MM,
            source=source.provider if source else None,
            parameter=PARAMETER_CODE,
            product=source.product if source else None,
            method="sum of daily totals over covered days only",
        ),
        Measurement(
            name="rainy_days",
            value=rainy_days,
            unit="days",
            source=source.provider if source else None,
            parameter=PARAMETER_CODE,
            product=source.product if source else None,
            method=f"days with precipitation >= {threshold} mm/day",
        ),
        Measurement(
            name="max_daily_rainfall",
            value=max_daily,
            unit=UNIT_MM,
            source=source.provider if source else None,
            parameter=PARAMETER_CODE,
            product=source.product if source else None,
            method="maximum daily total among covered days",
        ),
        Measurement(
            name="longest_observed_dry_spell",
            value=dry_spell.days,
            unit="days",
            source=source.provider if source else None,
            parameter=PARAMETER_CODE,
            product=source.product if source else None,
            method=(
                f"longest run of covered days below {threshold} mm/day; "
                f"contiguity={dry_spell.contiguity}"
            ),
        ),
    )

    missing = (
        MissingInput(
            name="soil_moisture",
            impact="Plant-available water and water stress cannot be assessed.",
            required_for="water stress",
        ),
        MissingInput(
            name="reference_evapotranspiration",
            impact="Irrigation demand and ET deficit cannot be estimated.",
            required_for="irrigation demand",
        ),
        MissingInput(
            name="irrigation_records",
            impact="Applied irrigation water is not recorded; only farmer-reported availability exists.",
            required_for="water balance",
        ),
    )

    drivers = (
        Driver(
            name="Rainfall over covered days",
            direction=DriverDirection.NEUTRAL,
            value=total,
            unit=UNIT_MM,
        ),
        Driver(
            name="Rainy days",
            direction=DriverDirection.NEUTRAL,
            value=rainy_days,
            unit="days",
        ),
        Driver(
            name="Observation coverage",
            direction=DriverDirection.NEUTRAL,
            value=f"{coverage.days_covered}/{coverage.days_expected} days",
        ),
    )

    limitations = [
        "Values are NASA POWER MERRA-2 grid-cell estimates for the farm's representative point, not on-farm measurements.",
        "The window ends at the latest available observation, not today.",
    ]
    if coverage.days_missing > 0:
        limitations.append(
            f"{coverage.days_missing} of {coverage.days_expected} days have no observation; "
            "the total covers observed days only and a continuous dry spell cannot be claimed."
        )
    if dry_spell.contiguity == INTERRUPTED:
        limitations.append(
            "Missing days interrupt the dry-spell search: the reported run is the longest observed "
            "consecutive run, not necessarily the true dry spell."
        )
    if not covered_values:
        limitations.append("No precipitation observation is available for this window.")

    return IndicatorResult(
        code="WATER",
        label="Water",
        status=status,
        confidence=confidence,
        period=period,
        coverage=coverage,
        summary=_summary(
            coverage=coverage,
            total=total,
            rainy_days=rainy_days,
            dry_spell=dry_spell,
            threshold=threshold,
        ),
        measurements=measurements,
        context=tuple(irrigation_context),
        drivers=drivers,
        missing=missing,
        methodology=WATER_METHODOLOGY,
        sources=(source,) if source else (),
        limitations=tuple(limitations),
    )


def _summary(
    *,
    coverage: Coverage,
    total: Decimal | None,
    rainy_days: int,
    dry_spell: DrySpell,
    threshold: Decimal,
) -> str:
    if coverage.days_covered == 0:
        return (
            "No precipitation observation is available in this window, so water "
            "conditions cannot be assessed."
        )

    coverage_text = (
        f"{coverage.days_covered} of {coverage.days_expected} days observed"
        if coverage.days_missing
        else f"all {coverage.days_expected} days observed"
    )
    total_text = f"{_fmt(total)} mm of rainfall over covered days"
    spell_text = (
        f"longest observed dry run {dry_spell.days} day(s)"
        if dry_spell.days is not None
        else "dry run not determinable"
    )
    if coverage.days_missing:
        return (
            f"{coverage_text}: {total_text}, {rainy_days} rainy day(s) at or above "
            f"{threshold} mm. {spell_text}; missing days mean this is an observed total, "
            "not a complete-window total."
        )
    return (
        f"{coverage_text}: {total_text}, {rainy_days} rainy day(s) at or above "
        f"{threshold} mm, {spell_text}."
    )


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return format(value.normalize(), "f")


__all__ = [
    "CONTIGUOUS",
    "INTERRUPTED",
    "PARAMETER_CODE",
    "UNKNOWN_CONTIGUITY",
    "WATER_METHODOLOGY",
    "DrySpell",
    "calculate_water_indicator",
    "default_rainy_day_threshold_mm",
]

"""Heat indicator calculations (Phase 4B).

Approved methodology (R16):

* ``T2M`` (daily mean), ``T2M_MAX`` and ``T2M_MIN`` come from the stored NASA
  POWER observations; no provider request happens here;
* generic, configurable **exposure** thresholds: hot day ``T2M_MAX >= 35 °C``,
  very hot day ``T2M_MAX >= 40 °C``, cool night ``T2M_MIN <= 5 °C``;
* a cool night is **not** evidence of frost and none of these numbers are
  crop-stress thresholds — crop-specific assessment belongs to Phase 5.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from django.conf import settings

from ..contract import (
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
    combine_coverage,
    confidence_for,
    count_days,
    coverage_from_values,
    days_in_window,
)

MEAN_PARAMETER = "T2M"
MAX_PARAMETER = "T2M_MAX"
MIN_PARAMETER = "T2M_MIN"
UNIT_C = "C"

HEAT_METHODOLOGY = Methodology(
    id="heat.exposure.v1",
    version="1.0.0",
    description=(
        "Air-temperature exposure summary over the latest available observation window: "
        "mean, mean daily maximum/minimum, and counts of days above/below generic "
        "air-temperature thresholds. Not a crop-stress assessment."
    ),
    threshold_source=(
        "Generic exposure bands, configurable via INDICATOR_HOT_DAY_C (35), "
        "INDICATOR_VERY_HOT_DAY_C (40) and INDICATOR_COOL_NIGHT_C (5). "
        "Not agricultural or crop-specific thresholds."
    ),
)


def default_hot_day_c() -> Decimal:
    return as_decimal(getattr(settings, "INDICATOR_HOT_DAY_C", None), "35")


def default_very_hot_day_c() -> Decimal:
    return as_decimal(getattr(settings, "INDICATOR_VERY_HOT_DAY_C", None), "40")


def default_cool_night_c() -> Decimal:
    return as_decimal(getattr(settings, "INDICATOR_COOL_NIGHT_C", None), "5")


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(Decimal("0.0001"))


def calculate_heat_indicator(
    *,
    mean_temperatures: Mapping[date, Decimal | None],
    max_temperatures: Mapping[date, Decimal | None],
    min_temperatures: Mapping[date, Decimal | None],
    start: date,
    end: date,
    today: date,
    hot_day_c: Decimal | None = None,
    very_hot_day_c: Decimal | None = None,
    cool_night_c: Decimal | None = None,
    sources: Mapping[str, SourceReference] | None = None,
) -> IndicatorResult:
    """Build the HEAT indicator from daily temperature series."""
    hot_threshold = hot_day_c or default_hot_day_c()
    very_hot_threshold = very_hot_day_c or default_very_hot_day_c()
    cool_threshold = cool_night_c or default_cool_night_c()
    sources = sources or {}

    days = days_in_window(start, end)
    means = {day: mean_temperatures.get(day) for day in days}
    maxima = {day: max_temperatures.get(day) for day in days}
    minima = {day: min_temperatures.get(day) for day in days}

    expected = count_days(start, end)
    coverage_by_parameter = {
        MEAN_PARAMETER: coverage_from_values(start, end, means, parameter=MEAN_PARAMETER).days_covered,
        MAX_PARAMETER: coverage_from_values(start, end, maxima, parameter=MAX_PARAMETER).days_covered,
        MIN_PARAMETER: coverage_from_values(start, end, minima, parameter=MIN_PARAMETER).days_covered,
    }
    coverage: Coverage = combine_coverage(expected, coverage_by_parameter)

    mean_values = [value for value in means.values() if value is not None]
    max_values = [value for value in maxima.values() if value is not None]
    min_values = [value for value in minima.values() if value is not None]

    mean_temperature = _mean(mean_values)
    mean_daily_max = _mean(max_values)
    mean_daily_min = _mean(min_values)
    # A count of zero requires at least one observed day for that parameter;
    # otherwise the count is unknown, never zero.
    hot_days = sum(1 for value in max_values if value >= hot_threshold) if max_values else None
    very_hot_days = (
        sum(1 for value in max_values if value >= very_hot_threshold) if max_values else None
    )
    cool_nights = sum(1 for value in min_values if value <= cool_threshold) if min_values else None

    latest_candidates = [
        day
        for day in days
        if means.get(day) is not None or maxima.get(day) is not None or minima.get(day) is not None
    ]
    period: Period = build_period(
        start=start,
        end=end,
        latest_observation=max(latest_candidates) if latest_candidates else None,
        today=today,
    )

    # INSUFFICIENT_DATA only when *no* temperature parameter has any value:
    # a fully missing parameter still leaves partial, useful measurements.
    has_any_data = any(count > 0 for count in coverage_by_parameter.values())
    if not has_any_data:
        status = IndicatorStatus.INSUFFICIENT_DATA
    elif coverage.days_missing > 0:
        status = IndicatorStatus.PARTIAL
    else:
        status = IndicatorStatus.OK

    confidence = confidence_for(coverage.ratio, cap=GRID_CELL_CONFIDENCE_CAP)

    def _measurement(
        name: str,
        value: Decimal | int | None,
        unit: str,
        parameter: str,
        method: str,
    ) -> Measurement:
        source = sources.get(parameter)
        return Measurement(
            name=name,
            value=value,
            unit=unit,
            source=source.provider if source else None,
            parameter=parameter,
            product=source.product if source else None,
            method=method,
        )

    measurements = (
        _measurement(
            "mean_temperature",
            mean_temperature,
            UNIT_C,
            MEAN_PARAMETER,
            "mean of daily mean temperature over covered days",
        ),
        _measurement(
            "mean_daily_maximum",
            mean_daily_max,
            UNIT_C,
            MAX_PARAMETER,
            "mean of daily maximum temperature over covered days",
        ),
        _measurement(
            "mean_daily_minimum",
            mean_daily_min,
            UNIT_C,
            MIN_PARAMETER,
            "mean of daily minimum temperature over covered days",
        ),
        _measurement(
            "hot_days",
            hot_days,
            "days",
            MAX_PARAMETER,
            f"days with maximum temperature >= {hot_threshold} °C",
        ),
        _measurement(
            "very_hot_days",
            very_hot_days,
            "days",
            MAX_PARAMETER,
            f"days with maximum temperature >= {very_hot_threshold} °C",
        ),
        _measurement(
            "cool_nights",
            cool_nights,
            "days",
            MIN_PARAMETER,
            f"days with minimum temperature <= {cool_threshold} °C (not a frost indicator)",
        ),
    )

    missing_inputs = [
        MissingInput(
            name="crop_heat_thresholds",
            impact="Crop-specific heat stress cannot be assessed; thresholds are generic air-temperature bands.",
            required_for="crop heat risk",
        ),
        MissingInput(
            name="growth_stage",
            impact="Exposure cannot be matched to sensitive crop stages.",
            required_for="crop heat risk",
        ),
    ]
    # Report parameters that produced no observation at all in this window.
    for parameter, count in coverage_by_parameter.items():
        if count == 0:
            missing_inputs.insert(
                0,
                MissingInput(
                    name=f"daily_{parameter.lower()}_observations",
                    impact=f"No {parameter} observation in this window; its metrics are not assessable.",
                    required_for="heat exposure",
                ),
            )
    missing = tuple(missing_inputs)

    drivers = (
        Driver(
            name="Hot days",
            direction=DriverDirection.NEGATIVE,
            value=hot_days,
            unit="days",
        ),
        Driver(
            name="Mean daily maximum",
            direction=DriverDirection.NEUTRAL,
            value=mean_daily_max,
            unit=UNIT_C,
        ),
        Driver(
            name="Observation coverage",
            direction=DriverDirection.NEUTRAL,
            value=f"{coverage.days_covered}/{coverage.days_expected} days",
        ),
    )

    limitations = [
        "Air-temperature exposure at a MERRA-2 grid cell, not a field or canopy measurement.",
        "Generic exposure bands only — not universal agricultural or crop-stress thresholds.",
        "A cool night below the threshold is not evidence of frost.",
        "The window ends at the latest available observation, not today.",
    ]
    if coverage.days_missing > 0:
        limitations.append(
            f"{coverage.days_missing} of {coverage.days_expected} days have no observation for at "
            "least one temperature parameter; means and counts cover observed days only."
        )
    if coverage.days_covered == 0:
        limitations.append("No temperature observation is available for this window.")

    return IndicatorResult(
        code="HEAT",
        label="Heat",
        status=status,
        confidence=confidence,
        period=period,
        coverage=coverage,
        summary=_summary(
            coverage=coverage,
            mean_daily_max=mean_daily_max,
            mean_daily_min=mean_daily_min,
            hot_days=hot_days,
            very_hot_days=very_hot_days,
            cool_nights=cool_nights,
            hot_threshold=hot_threshold,
        ),
        measurements=measurements,
        drivers=drivers,
        missing=missing,
        methodology=HEAT_METHODOLOGY,
        sources=tuple(sources.values()),
        limitations=tuple(limitations),
    )


def _summary(
    *,
    coverage: Coverage,
    mean_daily_max: Decimal | None,
    mean_daily_min: Decimal | None,
    hot_days: int | None,
    very_hot_days: int | None,
    cool_nights: int | None,
    hot_threshold: Decimal,
) -> str:
    if (
        mean_daily_max is None
        and mean_daily_min is None
        and hot_days is None
        and cool_nights is None
    ):
        return (
            "No air-temperature observation is available in this window, so heat "
            "exposure cannot be assessed."
        )

    coverage_text = (
        f"{coverage.days_covered} of {coverage.days_expected} days observed"
        if coverage.days_missing
        else f"all {coverage.days_expected} days observed"
    )
    hot_text = (
        f"{hot_days} day(s) at or above {hot_threshold} °C, {very_hot_days} at or above "
        "the very-hot band"
        if hot_days is not None
        else "daily maximum temperature unavailable"
    )
    cool_text = (
        f"{cool_nights} cool night(s)"
        if cool_nights is not None
        else "daily minimum temperature unavailable"
    )
    return (
        f"{coverage_text}: mean daily maximum {_fmt(mean_daily_max)} °C and mean daily "
        f"minimum {_fmt(mean_daily_min)} °C; {hot_text}; {cool_text}. "
        "Generic exposure only; not crop stress or frost."
    )


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return format(value.normalize(), "f")


__all__ = [
    "HEAT_METHODOLOGY",
    "MAX_PARAMETER",
    "MEAN_PARAMETER",
    "MIN_PARAMETER",
    "calculate_heat_indicator",
    "default_cool_night_c",
    "default_hot_day_c",
    "default_very_hot_day_c",
]
